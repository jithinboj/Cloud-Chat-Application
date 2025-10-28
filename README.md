# Cloud Chat — Real-time group chat with Python + Firestore

A minimal real-time group chat application:
- Python server: Flask + Flask-SocketIO
- Persistent storage: Firebase Firestore (via firebase-admin)
- Web client: served by Flask (Socket.IO client)

Features:
- Create / join chat rooms
- Real-time messaging via Socket.IO
- Message persistence in Firestore and room history (last 50 messages) on join
- Simple REST endpoint to list rooms

Prerequisites:
- Python 3.9+
- A Firebase project with Firestore enabled (Native mode)
- A Firebase service account JSON file for server access (create in Firebase Console → Project Settings → Service Accounts)

Setup
1. Clone or copy the files from this repo into a directory.

2. Create and activate a Python virtualenv:
   - python -m venv venv
   - source venv/bin/activate   (Linux / macOS)
   - venv\Scripts\activate      (Windows)

3. Install dependencies:
   - pip install -r requirements.txt

4. Put your Firebase service account JSON file somewhere safe, e.g. ./serviceAccount.json

5. Set the environment variable so the firebase-admin SDK can find it:
   - Linux / macOS:
     export GOOGLE_APPLICATION_CREDENTIALS="./serviceAccount.json"
   - Windows (PowerShell):
     $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\serviceAccount.json"

6. Start the server:
   - python app.py
   - The server runs on http://0.0.0.0:5000 by default.

7. Open a browser to http://localhost:5000, enter a username, create/join a room and chat. Open multiple windows or browsers to test real-time messaging.

Notes
- The server persists messages to Firestore in collection `messages`. Documents have fields:
  - room: string
  - username: string
  - content: string
  - timestamp: server UTC timestamp (stored as datetime)
- Rooms are tracked in collection `rooms` (document id == room name).
- This app uses Socket.IO for real-time messaging. The server is the single authority that emits messages to connected clients and persists them in Firestore.
