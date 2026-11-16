/**
 * ChatPulse — Socket.IO Connection & Event Dispatcher
 */

// Initialize Socket.IO client connection
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000
});

// Socket State
const SocketState = {
    isConnected: false,
    currentUserId: null
};

// Connection Established
socket.on('connect', () => {
    SocketState.isConnected = true;
    console.log('[WebSocket] Connected successfully with ID:', socket.id);
    
    // Update self status dot in UI
    const myDot = document.getElementById('my-status-dot');
    if (myDot) {
        myDot.className = 'status-indicator online';
    }
});

// Connection Lost / Disconnected
socket.on('disconnect', (reason) => {
    SocketState.isConnected = false;
    console.warn('[WebSocket] Disconnected from server:', reason);

    const myDot = document.getElementById('my-status-dot');
    if (myDot) {
        myDot.className = 'status-indicator offline';
    }
});

// Server Acknowledgement on Connect
socket.on('connected_ack', (data) => {
    console.log('[WebSocket] Handshake ACK:', data.message);
});

// Real-Time Online / Offline Status Broadcast
socket.on('user_status', (data) => {
    console.log('[WebSocket] User Status Update:', data);
    if (window.ChatApp && typeof window.ChatApp.onUserStatusChanged === 'function') {
        window.ChatApp.onUserStatusChanged(data);
    }
});

// Incoming Direct 1-to-1 Message
socket.on('new_direct_message', (msg) => {
    console.log('[WebSocket] New Direct Message:', msg);
    if (window.ChatApp && typeof window.ChatApp.onReceiveDirectMessage === 'function') {
        window.ChatApp.onReceiveDirectMessage(msg);
    }
});

// Incoming Chat Room Message
socket.on('new_room_message', (msg) => {
    console.log('[WebSocket] New Room Message:', msg);
    if (window.ChatApp && typeof window.ChatApp.onReceiveRoomMessage === 'function') {
        window.ChatApp.onReceiveRoomMessage(msg);
    }
});

// Room Notification (Join / Leave)
socket.on('room_notification', (data) => {
    console.log('[WebSocket] Room Notification:', data);
    if (window.ChatApp && typeof window.ChatApp.onRoomNotification === 'function') {
        window.ChatApp.onRoomNotification(data);
    }
});

// Live Typing Indicator
socket.on('typing_status', (data) => {
    if (window.ChatApp && typeof window.ChatApp.onTypingStatus === 'function') {
        window.ChatApp.onTypingStatus(data);
    }
});

// Messages Read Receipt
socket.on('messages_read_receipt', (data) => {
    if (window.ChatApp && typeof window.ChatApp.onMessagesReadReceipt === 'function') {
        window.ChatApp.onMessagesReadReceipt(data);
    }
});

// Error Notifications from Server
socket.on('error_notification', (data) => {
    alert(data.message || 'An error occurred.');
});
