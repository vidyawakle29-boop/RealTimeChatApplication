# 💬 ChatPulse — Modern Full-Stack Real-Time Chat Application

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Flask-SocketIO](https://img.shields.io/badge/Flask--SocketIO-5.3.6-red.svg?logo=socket.io&logoColor=white)](https://flask-socketio.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%203-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-d71f00.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A high-performance, internship-grade real-time chat platform engineered with **Python Flask**, **Flask-SocketIO**, and **SQLite**. Features instant bidirectional messaging, 1-to-1 private direct chats, collaborative multi-user chat rooms, live typing indicators, active online presence tracking, dark/light theme switching, and comprehensive automated test coverage.

---

## 🌟 Key Application Features

### 1. ⚡ Bidirectional Real-Time Communication
- **Event-Driven Architecture**: Uses native Flask-SocketIO events (`send_direct_message`, `send_room_message`, `typing_indicator`, `user_status`) over persistent WebSockets.
- **Zero-Polling Message Delivery**: Messages render immediately across connected clients without refreshing the page.
- **Auto-Reconnection**: Resilient client-side WebSocket manager automatically reconnects upon temporary network drops.

### 2. 🔒 Secure User Authentication & Session Management
- **Registration & Login**: Strict validation for usernames (3-30 chars, alphanumeric + underscores) and email addresses.
- **Cryptographic Hashing**: Secure password encryption via Werkzeug (`scrypt`/`pbkdf2`).
- **Duplicate Prevention**: Real-time uniqueness enforcement preventing duplicate usernames or emails.
- **Session Protection**: Flask-Login session management with `HttpOnly` and `SameSite=Lax` cookie flags.
- **Access Control**: `@login_required` route guards preventing unauthorized access to chats or APIs.

### 3. 💬 1-to-1 Private Direct Messaging
- **Dedicated Private Rooms**: Socket.IO channels scoped per user (`user_<id>`) for private message delivery.
- **Chronological Chat History**: Fully persistent message history loaded from SQLite via Flask-SQLAlchemy.
- **Delivery & Read Receipts**: Visual status checkmarks (`✓✓`) updating in real-time when messages are read.
- **Unread Message Badges**: Dynamic counters on sidebar conversations.

### 4. 📢 Chat Rooms & Group Channels
- **Create & Discover Rooms**: Users can create custom channels or join existing community rooms (e.g., `#General`, `#Tech-Discussion`).
- **Dynamic Membership**: Instant join/leave actions with automatic channel synchronization.
- **Join/Leave Notifications**: Live system notices broadcast when members join or leave the room.
- **Room History**: Full historical message persistence for all room members.

### 5. ⌨️ Live Typing Indicators & Online Presence
- **Typing Status**: Live feedback displaying *"User is typing..."* when a contact begins composing a message.
- **Automatic Debounce**: Stops typing indicator automatically after inactivity.
- **Dynamic Online Presence**: Tracks connected sockets in real-time with green/gray presence badges and last-seen timestamps.

### 6. 🎨 Modern Responsive UI / UX
- **Theme Engine**: Seamless toggle between Dark and Light mode with persistent `localStorage` preference.
- **Glassmorphic Sidebar**: Profile widget, tab navigation (Direct, Rooms, People), live search filter, and unread counters.
- **Interactive Message Bubbles**: Distinct outgoing (indigo) and incoming (neutral) bubbles with timestamps and avatar indicators.
- **Mobile Responsive Drawer**: Auto-collapsing sidebar and mobile back button for smooth navigation on phones and tablets.
- **Quick Emoji Drawer**: Instant emoji picker for fast reactions.

---

## 🏗️ Project Architecture & Folder Structure

```text
real-time-chat-application/
│
├── app/
│   ├── __init__.py          # Application Factory (create_app), Blueprints & Security Headers
│   ├── models.py            # User, ChatRoom, RoomMember, Message SQLAlchemy models
│   ├── extensions.py        # db, socketio, login_manager instances
│   │
│   ├── auth/                # Authentication Blueprint
│   │   ├── __init__.py
│   │   └── routes.py        # Register, Login, Logout, Profile endpoints
│   │
│   ├── chat/                # Real-Time & Chat Blueprint
│   │   ├── __init__.py
│   │   ├── routes.py        # REST APIs for conversations, users, rooms, and history
│   │   └── events.py        # Socket.IO event handlers (connect, message, typing, rooms)
│   │
│   ├── templates/           # Jinja2 Modular Templates
│   │   ├── base.html        # Master layout with FontAwesome, Socket.IO & theme engine
│   │   ├── index.html       # Public landing page with hero, mockup, and features
│   │   ├── login.html       # Clean glassmorphic login page
│   │   ├── register.html    # Registration page with live username availability check
│   │   ├── dashboard.html   # Real-time chat workspace (sidebar, feed, modals)
│   │   └── profile.html     # User profile, statistics, and avatar customizer
│   │
│   └── static/              # Frontend Assets
│       ├── css/
│       │   └── style.css    # Modern Untitled-style design system with Dark/Light themes
│       └── js/
│           ├── socket.js    # Socket.IO connection manager & WebSocket dispatcher
│           └── chat.js      # Main UI controller, feed renderer, typing & modals
│
├── tests/                   # Automated Unit & Integration Test Suite
│   ├── __init__.py
│   ├── test_models.py       # Database schema, hashing & relationship tests
│   ├── test_auth.py         # Registration, duplicate checks, login, logout & routes
│   └── test_chat.py         # API endpoints & Socket.IO real-time delivery tests
│
├── instance/
│   └── chat.db              # SQLite Database File
│
├── config.py                # Development, Testing, Production configurations
├── run.py                   # Development server entry point with socketio.run
├── seed.py                  # Database Seeder with demo users, rooms & history
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Comprehensive Git ignore rules
└── README.md                # Project documentation
```

---

## 🚀 Quickstart & Installation (Windows PowerShell)

### Prerequisites
- **Python 3.10+** installed on your system.
- **Git** (optional, for GitHub version control).

---

### Step 1: Open Project Directory
```powershell
cd "c:\Users\HP\Downloads\blogging platform\real-time-chat-application"
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Seed Demo Data (Optional but Recommended)
Populate test accounts (`vidya`, `alice`, `bob`, `charlie`) and sample chat rooms:
```powershell
python seed.py
```
> **Demo Accounts Credentials:**
> - `Username: vidya` | `Password: password123`
> - `Username: alice` | `Password: password123`
> - `Username: bob` | `Password: password123`
> - `Username: charlie` | `Password: password123`

### Step 5: Start the Real-Time Chat Server
```powershell
python run.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Running the Automated Test Suite

The project includes automated tests for database models, user authentication, REST APIs, and **real-time Socket.IO WebSocket messaging** using an in-memory SQLite database:

```powershell
python -m unittest discover tests -v
```

Or using `pytest`:
```powershell
pytest -v
```

### Verified Test Cases:
- ✅ **Password Hashing & Verification**: Werkzeug `scrypt` hashing integrity.
- ✅ **User Serialization & Initials Avatars**: JSON payloads and dynamic avatars.
- ✅ **Chat Room & Membership Operations**: Room creation, member counting, membership checks.
- ✅ **Message Creation & Read Receipts**: Dual 1-to-1 and room message representations.
- ✅ **Registration Validation**: Enforces valid usernames, emails, and passwords.
- ✅ **Duplicate Prevention**: Blocks duplicate username/email registrations.
- ✅ **User Login & Session Termination**: Session establishment, cookie flags, and clean logout.
- ✅ **Protected Route Enforcement**: Unauthorized redirects to login page.
- ✅ **Socket.IO Authentication Handshake**: Drops unauthenticated WebSocket connections.
- ✅ **Real-Time Direct Messaging**: Message delivery across user channels and database persistence.
- ✅ **Group Room Messaging**: Multi-user broadcast within room channels.
- ✅ **Live Typing Indicators**: Real-time typing status propagation.

---

## 🔒 Security & Best Practices

1. **Password Security**: Passwords are never stored in plaintext. Werkzeug's secure hashing algorithm is used with automatic salting.
2. **XSS Protection**: All incoming and outgoing message strings are sanitized using HTML entity escaping before rendering in the DOM.
3. **CSRF & Session Hardening**: Sessions configured with `HttpOnly` and `SameSite=Lax` cookies.
4. **WebSocket Authorization**: Socket.IO connection event enforces authentication via `current_user.is_authenticated`.
5. **Channel Isolation**: Private direct messages are sent exclusively to target recipient rooms (`user_<id>`), preventing eavesdropping.

---

## 🔮 Future Enhancements
- 📎 **File & Media Attachments**: Upload photos, documents, and voice notes.
- 🎙️ **Voice & Video Calling**: WebRTC peer-to-peer audio/video calls.
- 🔔 **Web Push Notifications**: Browser push notifications for offline messages.
- 📌 **Pinned Messages & Mentions**: `@username` tagging and pinned room announcements.

---

## 👨‍💻 Author

**Vidya Ratan Wakle**
- Role: Full-Stack Python Developer & Software Architect
- Project: Real-Time Chat Application with Flask-SocketIO

---

## 📤 GitHub Upload Instructions

To upload this clean project to your own GitHub repository:

```powershell
# 1. Navigate to the project root
cd "c:\Users\HP\Downloads\blogging platform\real-time-chat-application"

# 2. Initialize a new Git repository
git init

# 3. Stage all files (respects .gitignore)
git add .

# 4. Commit files
git commit -m "feat: complete real-time chat application with Flask-SocketIO"

# 5. Create a new repository on GitHub (e.g., https://github.com/your-username/real-time-chat-application.git)

# 6. Link remote and push
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main
```

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
