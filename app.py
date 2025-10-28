import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
import firebase_admin
from firebase_admin import credentials, firestore

# Configuration
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
MAX_HISTORY = 50  # messages to return when joining a room

# Initialize Flask
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Use eventlet for async support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# --- Initialize Firebase Admin / Firestore ---
# The firebase-admin SDK looks for GOOGLE_APPLICATION_CREDENTIALS environment variable by default.
# Set environment var to path of your service account JSON before running.
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    raise RuntimeError(
        "Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to the path of your Firebase service account JSON."
    )

cred = credentials.ApplicationDefault()
default_app = firebase_admin.initialize_app(cred)
db = firestore.client()

# Helper: serialize Firestore document to JSON-friendly dict
def serialize_message(doc_dict):
    result = {
        "id": doc_dict.get("_id", ""),
        "room": doc_dict.get("room", ""),
        "username": doc_dict.get("username", ""),
        "content": doc_dict.get("content", ""),
    }
    ts = doc_dict.get("timestamp")
    if ts:
        # datetime -> ISO 8601 string in UTC
        try:
            # If timezone-aware
            result["timestamp"] = ts.astimezone(timezone.utc).isoformat()
        except Exception:
            # Fallback for naive datetimes
            result["timestamp"] = datetime(
                ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, tzinfo=timezone.utc
            ).isoformat()
    else:
        result["timestamp"] = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    return result

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/rooms", methods=["GET"])
def list_rooms():
    rooms_ref = db.collection("rooms")
    docs = rooms_ref.stream()
    rooms = []
    for d in docs:
        data = d.to_dict() or {}
        rooms.append({"id": d.id, "name": data.get("name", d.id)})
    return jsonify({"rooms": rooms})

# --- Socket.IO events ---
@socketio.on("join")
def handle_join(data):
    """
    data = {
        "room": "room-name",
        "username": "Alice"
    }
    """
    room = data.get("room")
    username = data.get("username", "Anonymous")
    if not room:
        emit("error", {"message": "Missing room name in join request."})
        return

    join_room(room)

    # Ensure room exists in Firestore
    db.collection("rooms").document(room).set({"name": room}, merge=True)

    # Load history
    messages_ref = (
        db.collection("messages")
        .where("room", "==", room)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(MAX_HISTORY)
    )
    docs = messages_ref.stream()
    history = []
    for doc in docs:
        d = doc.to_dict()
        d["_id"] = doc.id
        history.append(serialize_message(d))
    # reverse to chronological order
    history.reverse()

    # Send history to the joining client
    emit("room_history", {"room": room, "messages": history})

    # Notify room members that a user joined
    emit("user_joined", {"room": room, "username": username}, room=room)

@socketio.on("leave")
def handle_leave(data):
    """
    data = {
        "room": "room-name",
        "username": "Alice"
    }
    """
    room = data.get("room")
    username = data.get("username", "Anonymous")
    if not room:
        return
    leave_room(room)
    emit("user_left", {"room": room, "username": username}, room=room)

@socketio.on("send_message")
def handle_send_message(data):
    """
    data = {
        "room": "room-name",
        "username": "Alice",
        "content": "Hello!"
    }
    """
    room = data.get("room")
    username = data.get("username", "Anonymous")
    content = data.get("content", "")
    if not room or not content:
        emit("error", {"message": "Missing room or content in message."})
        return

    # Build message
    ts = datetime.utcnow().replace(tzinfo=timezone.utc)
    message = {
        "room": room,
        "username": username,
        "content": content,
        "timestamp": ts,
    }

    # Persist to Firestore
    doc_ref = db.collection("messages").document()
    doc_ref.set(message)

    # Ensure room exists in Firestore
    db.collection("rooms").document(room).set({"name": room}, merge=True)

    # Broadcast to room
    payload = serialize_message({**message, "_id": doc_ref.id})
    emit("new_message", payload, room=room)

@socketio.on("connect")
def handle_connect():
    # optional: you can emit a welcome event here
    emit("connected", {"message": "Connected to chat server."})

@socketio.on("disconnect")
def handle_disconnect():
    # optional: handle cleanup
    pass

# Run App
if __name__ == "__main__":
    print("Starting Chat server on {}:{}".format(HOST, PORT))
    socketio.run(app, host=HOST, port=PORT)
