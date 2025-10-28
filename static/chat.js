(function () {
  const socket = io();

  // DOM elements
  const usernameInput = document.getElementById("username");
  const roomInput = document.getElementById("room-input");
  const joinBtn = document.getElementById("join-btn");
  const roomsList = document.getElementById("rooms-list");
  const messagesDiv = document.getElementById("messages");
  const messageInput = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");

  let currentRoom = null;
  let username = null;

  // Helpers
  function appendMessage(msg) {
    const el = document.createElement("div");
    el.className = "message";
    const ts = msg.timestamp ? new Date(msg.timestamp).toLocaleString() : "";
    el.innerHTML = '<div class="meta"><span class="username">' + escapeHtml(msg.username) + '</span><span class="meta-ts">' + ts + '</span></div>' +
                   '<div class="content">' + escapeHtml(msg.content) + '</div>';
    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function escapeHtml(s) {
    if (!s) return "";
    return s.replace(/[&<>"'`=\/]/g, function (ch) {
      return ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '/': '&#x2F;', '`': '&#x60;', '=': '&#x3D;'
      })[ch];
    });
  }

  function setActiveRoom(room) {
    currentRoom = room;
    // update room list active class
    Array.from(roomsList.children).forEach((r) => {
      if (r.dataset.room === room) {
        r.classList.add("active");
      } else {
        r.classList.remove("active");
      }
    });
    messagesDiv.innerHTML = "";
  }

  // Load rooms via REST
  function loadRooms() {
    fetch("/api/rooms")
      .then((r) => r.json())
      .then((data) => {
        roomsList.innerHTML = "";
        (data.rooms || []).forEach((room) => {
          const el = document.createElement("div");
          el.className = "room";
          el.dataset.room = room.id;
          el.textContent = room.name;
          el.addEventListener("click", () => {
            joinRoom(room.id);
          });
          roomsList.appendChild(el);
        });
      })
      .catch((err) => {
        console.error("Failed to load rooms", err);
      });
  }

  // Join a room
  function joinRoom(room) {
    if (!room) return;
    username = (usernameInput.value || "Anonymous").trim();
    if (!username) username = "Anonymous";
    setActiveRoom(room);
    socket.emit("join", { room: room, username: username });
  }

  // Send message
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !currentRoom) return;
    username = (usernameInput.value || "Anonymous").trim() || "Anonymous";
    socket.emit("send_message", { room: currentRoom, username: username, content: content });
    messageInput.value = "";
  }

  // Event listeners
  joinBtn.addEventListener("click", () => {
    const room = (roomInput.value || "").trim();
    if (!room) return;
    joinRoom(room);
    // re-load rooms after small delay to show the new room
    setTimeout(loadRooms, 500);
  });

  sendBtn.addEventListener("click", () => {
    sendMessage();
  });

  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });

  // Socket event handlers
  socket.on("connect", () => {
    console.log("Connected to server");
    loadRooms();
  });

  socket.on("room_history", (data) => {
    if (!data || !data.room) return;
    // If we're not in this room, ignore
    if (data.room !== currentRoom) return;
    messagesDiv.innerHTML = "";
    const messages = data.messages || [];
    messages.forEach((m) => appendMessage(m));
  });

  socket.on("new_message", (msg) => {
    if (!msg) return;
    if (msg.room !== currentRoom) return;
    appendMessage(msg);
  });

  socket.on("user_joined", (data) => {
    if (!data || data.room !== currentRoom) return;
    const el = document.createElement("div");
    el.className = "meta";
    el.textContent = `${data.username} joined the room.`;
    messagesDiv.appendChild(el);
  });

  socket.on("user_left", (data) => {
    if (!data || data.room !== currentRoom) return;
    const el = document.createElement("div");
    el.className = "meta";
    el.textContent = `${data.username} left the room.`;
    messagesDiv.appendChild(el);
  });

  socket.on("error", (err) => {
    console.error("Socket error:", err);
  });

  // initial load
  loadRooms();
})();
