/**
 * ChatPulse — Main Frontend Controller & UI State Manager
 */

const ChatState = {
    currentUserId: null,
    currentUsername: '',
    currentUserAvatar: '',
    activeChat: null, // { type: 'user' | 'room', id: number, title: string, avatar: string, isOnline: boolean }
    directChats: [],
    rooms: [],
    directory: [],
    typingTimeout: null,
    isCurrentlyTyping: false
};

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    // Read user identity from DOM
    const uidElem = document.getElementById('current-user-id');
    const uNameElem = document.getElementById('current-username');
    const uAvatarElem = document.getElementById('current-user-avatar');

    if (uidElem && uidElem.value) {
        ChatState.currentUserId = parseInt(uidElem.value, 10);
        ChatState.currentUsername = uNameElem ? uNameElem.value : '';
        ChatState.currentUserAvatar = uAvatarElem ? uAvatarElem.value : '';
        SocketState.currentUserId = ChatState.currentUserId;
    }

    // Attach Textarea keyboard listeners for Enter send and typing events
    setupInputListeners();

    // Attach Sidebar Search
    setupSidebarSearch();

    // Initial Data Fetch
    loadConversations();
    loadDirectory();
});

// ==================== DATA FETCHING ====================

/**
 * Loads active direct conversations and joined rooms from API
 */
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        if (!response.ok) throw new Error('Failed to load conversations');

        const data = await response.json();
        ChatState.directChats = data.direct || [];
        ChatState.rooms = data.rooms || [];

        renderDirectChatsList(ChatState.directChats);
        renderRoomsList(ChatState.rooms);
        updateUnreadBadges();
    } catch (err) {
        console.error('[ChatApp] Error loading conversations:', err);
    }
}

/**
 * Loads user directory for search and starting new chats
 */
async function loadDirectory(query = '') {
    try {
        const url = query ? `/api/users?q=${encodeURIComponent(query)}` : '/api/users';
        const response = await fetch(url);
        if (!response.ok) return;

        const users = await response.json();
        ChatState.directory = users;
        renderDirectoryList(users);
    } catch (err) {
        console.error('[ChatApp] Error loading user directory:', err);
    }
}

// ==================== RENDERING SIDEBAR ====================

function renderDirectChatsList(chats) {
    const container = document.getElementById('direct-chats-list');
    if (!container) return;

    if (!chats || chats.length === 0) {
        container.innerHTML = `
            <div class="sidebar-empty">
                <i class="fa-regular fa-message" style="font-size: 1.5rem; margin-bottom: 8px; display: block;"></i>
                No direct messages yet.<br>Click <strong>+ New Chat</strong> to begin.
            </div>
        `;
        return;
    }

    container.innerHTML = chats.map(item => {
        const u = item.user;
        const isActive = ChatState.activeChat && ChatState.activeChat.type === 'user' && ChatState.activeChat.id === u.id;
        const unreadBadge = item.unread_count > 0 ? `<span class="unread-badge">${item.unread_count}</span>` : '';
        const onlineClass = u.is_online ? 'online' : 'offline';
        const snippet = item.last_message ? escapeHtml(item.last_message) : 'No messages yet';

        return `
            <div class="conversation-item ${isActive ? 'active' : ''}" 
                 id="direct-item-${u.id}"
                 onclick="selectDirectChat(${u.id}, '${escapeAttr(u.username)}', '${escapeAttr(u.avatar)}', ${u.is_online})">
                <div class="item-avatar-wrap">
                    <img src="${escapeAttr(u.avatar)}" alt="${escapeAttr(u.username)}">
                    <span class="status-indicator ${onlineClass}" id="user-dot-${u.id}"></span>
                </div>
                <div class="item-info">
                    <div class="item-info-top">
                        <span class="item-title">${escapeHtml(u.username)}</span>
                        <span class="item-time">${escapeHtml(item.last_message_time || '')}</span>
                    </div>
                    <div class="item-info-bottom">
                        <span class="item-snippet" id="direct-snippet-${u.id}">${snippet}</span>
                        ${unreadBadge}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderRoomsList(rooms) {
    const container = document.getElementById('rooms-list');
    if (!container) return;

    if (!rooms || rooms.length === 0) {
        container.innerHTML = `
            <div class="sidebar-empty">
                <i class="fa-solid fa-hashtag" style="font-size: 1.5rem; margin-bottom: 8px; display: block;"></i>
                No rooms joined yet.<br>Click <strong>+ Room</strong> to create or join one.
            </div>
        `;
        return;
    }

    container.innerHTML = rooms.map(item => {
        const r = item.room;
        const isActive = ChatState.activeChat && ChatState.activeChat.type === 'room' && ChatState.activeChat.id === r.id;
        const snippet = item.last_message ? escapeHtml(item.last_message) : 'No messages yet';

        return `
            <div class="conversation-item ${isActive ? 'active' : ''}" 
                 id="room-item-${r.id}"
                 onclick="selectRoomChat(${r.id}, '${escapeAttr(r.room_name)}', '${escapeAttr(r.description)}', ${r.member_count})">
                <div class="item-avatar-wrap">
                    <div class="room-icon-avatar">
                        <i class="fa-solid fa-hashtag"></i>
                    </div>
                </div>
                <div class="item-info">
                    <div class="item-info-top">
                        <span class="item-title">${escapeHtml(r.room_name)}</span>
                        <span class="item-time">${escapeHtml(item.last_message_time || '')}</span>
                    </div>
                    <div class="item-info-bottom">
                        <span class="item-snippet" id="room-snippet-${r.id}">${snippet}</span>
                        <span class="item-time"><i class="fa-solid fa-users"></i> ${r.member_count}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderDirectoryList(users) {
    const container = document.getElementById('directory-list');
    if (!container) return;

    if (!users || users.length === 0) {
        container.innerHTML = `<div class="sidebar-empty">No other registered users found.</div>`;
        return;
    }

    container.innerHTML = users.map(u => {
        const onlineClass = u.is_online ? 'online' : 'offline';
        const statusText = u.is_online ? 'Online' : 'Offline';

        return `
            <div class="conversation-item" 
                 onclick="selectDirectChat(${u.id}, '${escapeAttr(u.username)}', '${escapeAttr(u.avatar)}', ${u.is_online})">
                <div class="item-avatar-wrap">
                    <img src="${escapeAttr(u.avatar)}" alt="${escapeAttr(u.username)}">
                    <span class="status-indicator ${onlineClass}"></span>
                </div>
                <div class="item-info">
                    <div class="item-info-top">
                        <span class="item-title">${escapeHtml(u.username)}</span>
                        <span class="item-time ${u.is_online ? 'text-success' : ''}">${statusText}</span>
                    </div>
                    <div class="item-info-bottom">
                        <span class="item-snippet">${escapeHtml(u.bio || 'Available for chat')}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function updateUnreadBadges() {
    let totalUnread = 0;
    ChatState.directChats.forEach(item => {
        totalUnread += (item.unread_count || 0);
    });

    const badge = document.getElementById('direct-unread-badge');
    if (badge) {
        if (totalUnread > 0) {
            badge.textContent = totalUnread;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

// ==================== CHAT SELECTION & HISTORY ====================

/**
 * Select a 1-to-1 direct conversation
 */
async function selectDirectChat(partnerId, partnerUsername, partnerAvatar, isOnline) {
    ChatState.activeChat = {
        type: 'user',
        id: partnerId,
        title: partnerUsername,
        avatar: partnerAvatar,
        isOnline: isOnline
    };

    // Update Header UI
    document.getElementById('chat-empty-state').classList.add('hidden');
    document.getElementById('chat-active-panel').classList.remove('hidden');

    const headerTitle = document.getElementById('chat-header-title');
    const headerSubtitle = document.getElementById('chat-status-text');
    const headerAvatar = document.getElementById('chat-header-avatar');
    const headerDot = document.getElementById('chat-header-status-dot');
    const leaveBtn = document.getElementById('leave-room-header-btn');

    headerTitle.textContent = partnerUsername;
    headerAvatar.src = partnerAvatar;
    headerDot.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
    headerSubtitle.textContent = isOnline ? 'Active Now' : 'Offline';
    leaveBtn.style.display = 'none';

    // Highlight active item in sidebar
    updateActiveSidebarItem();

    // Mark messages read locally & reset badge
    const chatItem = ChatState.directChats.find(c => c.user.id === partnerId);
    if (chatItem) {
        chatItem.unread_count = 0;
        updateUnreadBadges();
        renderDirectChatsList(ChatState.directChats);
    }

    // Socket emit mark as read
    socket.emit('mark_read_event', { sender_id: partnerId });

    // Fetch and render direct message history
    try {
        const response = await fetch(`/api/messages/direct/${partnerId}`);
        if (!response.ok) throw new Error('Failed to fetch messages');
        const data = await response.json();
        renderMessages(data.messages || [], 'user');
    } catch (err) {
        console.error('[ChatApp] Error fetching direct messages:', err);
    }

    // On mobile screens, collapse sidebar to show chat panel
    if (window.innerWidth <= 768) {
        document.getElementById('chat-sidebar').classList.add('collapsed');
    }

    // Focus input
    document.getElementById('message-input').focus();
}

/**
 * Select a group chat room
 */
async function selectRoomChat(roomId, roomName, description, memberCount) {
    ChatState.activeChat = {
        type: 'room',
        id: roomId,
        title: roomName,
        avatar: '',
        description: description,
        memberCount: memberCount
    };

    // Update Header UI
    document.getElementById('chat-empty-state').classList.add('hidden');
    document.getElementById('chat-active-panel').classList.remove('hidden');

    const headerTitle = document.getElementById('chat-header-title');
    const headerSubtitle = document.getElementById('chat-status-text');
    const headerAvatar = document.getElementById('chat-header-avatar');
    const headerDot = document.getElementById('chat-header-status-dot');
    const leaveBtn = document.getElementById('leave-room-header-btn');

    headerTitle.textContent = `#${roomName}`;
    headerAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(roomName)}&background=4f46e5&color=fff&bold=true`;
    headerDot.className = 'status-indicator online';
    headerSubtitle.textContent = `${memberCount} members • ${description || 'Public Channel'}`;
    leaveBtn.style.display = 'inline-flex';

    // Highlight active item in sidebar
    updateActiveSidebarItem();

    // Join room channel in socket
    socket.emit('join_room_event', { room_id: roomId });

    // Fetch and render room message history
    try {
        const response = await fetch(`/api/messages/room/${roomId}`);
        if (!response.ok) throw new Error('Failed to fetch room messages');
        const data = await response.json();
        renderMessages(data.messages || [], 'room');
    } catch (err) {
        console.error('[ChatApp] Error fetching room messages:', err);
    }

    if (window.innerWidth <= 768) {
        document.getElementById('chat-sidebar').classList.add('collapsed');
    }

    document.getElementById('message-input').focus();
}

function updateActiveSidebarItem() {
    document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
    if (!ChatState.activeChat) return;

    const idPrefix = ChatState.activeChat.type === 'user' ? 'direct-item-' : 'room-item-';
    const activeEl = document.getElementById(`${idPrefix}${ChatState.activeChat.id}`);
    if (activeEl) activeEl.classList.add('active');
}

// ==================== MESSAGE FEED RENDERING ====================

function renderMessages(messages, chatType) {
    const feed = document.getElementById('messages-feed');
    if (!feed) return;

    if (!messages || messages.length === 0) {
        feed.innerHTML = `
            <div class="system-notice">
                <i class="fa-solid fa-lock"></i>
                <span>This is the start of your message history with <strong>${escapeHtml(ChatState.activeChat.title)}</strong>.</span>
            </div>
        `;
        return;
    }

    let html = '';
    let lastDate = '';

    messages.forEach(msg => {
        // Date divider check
        const msgDate = msg.date_display || '';
        if (msgDate && msgDate !== lastDate) {
            html += `<div class="date-divider"><span>${escapeHtml(msgDate)}</span></div>`;
            lastDate = msgDate;
        }

        const isSentByMe = msg.sender_id === ChatState.currentUserId;
        const bubbleClass = isSentByMe ? 'sent' : 'received';

        // Sender name for group chats if not sent by me
        const senderName = (!isSentByMe && chatType === 'room') 
            ? `<span class="msg-sender-name">${escapeHtml(msg.sender_username || 'Member')}</span>` 
            : '';

        // Avatar for received messages
        const avatarImg = (!isSentByMe)
            ? `<img src="${escapeAttr(msg.sender_avatar || 'https://ui-avatars.com/api/?name=User')}" class="msg-avatar" alt="Avatar">`
            : '';

        // Read receipt double-check for sent messages
        const readReceipt = isSentByMe 
            ? `<i class="fa-solid fa-check-double read-check ${msg.is_read ? 'read' : ''}" title="${msg.is_read ? 'Read' : 'Delivered'}"></i>` 
            : '';

        html += `
            <div class="message-bubble-row ${bubbleClass}" id="msg-${msg.id}">
                ${avatarImg}
                <div class="bubble-card">
                    ${senderName}
                    <div class="msg-text">${escapeHtml(msg.message)}</div>
                    <div class="msg-meta">
                        <span class="msg-time">${escapeHtml(msg.time_display || '')}</span>
                        ${readReceipt}
                    </div>
                </div>
            </div>
        `;
    });

    feed.innerHTML = html;
    scrollToBottom();
}

function appendSingleMessage(msg, chatType) {
    const feed = document.getElementById('messages-feed');
    if (!feed) return;

    const isSentByMe = msg.sender_id === ChatState.currentUserId;
    const bubbleClass = isSentByMe ? 'sent' : 'received';

    const senderName = (!isSentByMe && chatType === 'room') 
        ? `<span class="msg-sender-name">${escapeHtml(msg.sender_username || 'Member')}</span>` 
        : '';

    const avatarImg = (!isSentByMe)
        ? `<img src="${escapeAttr(msg.sender_avatar || 'https://ui-avatars.com/api/?name=User')}" class="msg-avatar" alt="Avatar">`
        : '';

    const readReceipt = isSentByMe 
        ? `<i class="fa-solid fa-check-double read-check ${msg.is_read ? 'read' : ''}"></i>` 
        : '';

    const row = document.createElement('div');
    row.className = `message-bubble-row ${bubbleClass}`;
    row.id = `msg-${msg.id}`;
    row.innerHTML = `
        ${avatarImg}
        <div class="bubble-card">
            ${senderName}
            <div class="msg-text">${escapeHtml(msg.message)}</div>
            <div class="msg-meta">
                <span class="msg-time">${escapeHtml(msg.time_display || '')}</span>
                ${readReceipt}
            </div>
        </div>
    `;

    feed.appendChild(row);
    scrollToBottom();
}

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// ==================== SENDING MESSAGES ====================

function handleSendMessage(event) {
    if (event) event.preventDefault();
    if (!ChatState.activeChat) return;

    const input = document.getElementById('message-input');
    const rawText = input.value.trim();
    if (!rawText) return;

    // Direct Message
    if (ChatState.activeChat.type === 'user') {
        socket.emit('send_direct_message', {
            receiver_id: ChatState.activeChat.id,
            message: rawText
        });
    } 
    // Room Message
    else if (ChatState.activeChat.type === 'room') {
        socket.emit('send_room_message', {
            room_id: ChatState.activeChat.id,
            message: rawText
        });
    }

    // Clear input & reset typing
    input.value = '';
    stopTyping();
}

// ==================== WEBSOCKET EVENT HOOKS ====================

const ChatApp = {
    /**
     * Handlers invoked by socket.js
     */
    onReceiveDirectMessage(msg) {
        // If the active conversation is with either the sender or receiver
        const isCurrentChat = ChatState.activeChat && 
            ChatState.activeChat.type === 'user' && 
            (ChatState.activeChat.id === msg.sender_id || (msg.sender_id === ChatState.currentUserId && ChatState.activeChat.id === msg.receiver_id));

        if (isCurrentChat) {
            appendSingleMessage(msg, 'user');
            // If incoming from partner, mark read immediately
            if (msg.sender_id !== ChatState.currentUserId) {
                socket.emit('mark_read_event', { sender_id: msg.sender_id });
            }
        }

        // Update sidebar conversations
        loadConversations();
    },

    onReceiveRoomMessage(msg) {
        if (ChatState.activeChat && ChatState.activeChat.type === 'room' && ChatState.activeChat.id === msg.room_id) {
            appendSingleMessage(msg, 'room');
        }

        // Update snippet in sidebar
        const snippetEl = document.getElementById(`room-snippet-${msg.room_id}`);
        if (snippetEl) {
            snippetEl.textContent = `${msg.sender_username}: ${msg.message}`;
        }
    },

    onRoomNotification(data) {
        if (ChatState.activeChat && ChatState.activeChat.type === 'room' && ChatState.activeChat.id === data.room_id) {
            const feed = document.getElementById('messages-feed');
            if (feed) {
                const notice = document.createElement('div');
                notice.className = 'system-notice';
                notice.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>${escapeHtml(data.message)}</span>`;
                feed.appendChild(notice);
                scrollToBottom();
            }
        }
    },

    onTypingStatus(data) {
        if (!ChatState.activeChat) return;

        const isMatch = (ChatState.activeChat.type === data.recipient_type) &&
            ((data.recipient_type === 'user' && ChatState.activeChat.id === data.user_id) ||
             (data.recipient_type === 'room' && ChatState.activeChat.id === data.room_id));

        if (!isMatch) return;

        const typingBar = document.getElementById('typing-indicator-bar');
        const typingLabel = document.getElementById('typing-text-label');

        if (data.is_typing) {
            typingLabel.textContent = `${data.username} is typing...`;
            typingBar.classList.remove('hidden');
        } else {
            typingBar.classList.add('hidden');
        }
    },

    onUserStatusChanged(data) {
        // Update user status dot in sidebar
        const userDot = document.getElementById(`user-dot-${data.user_id}`);
        if (userDot) {
            userDot.className = `status-indicator ${data.status === 'online' ? 'online' : 'offline'}`;
        }

        // Update active chat header if current chat is this user
        if (ChatState.activeChat && ChatState.activeChat.type === 'user' && ChatState.activeChat.id === data.user_id) {
            const headerDot = document.getElementById('chat-header-status-dot');
            const headerText = document.getElementById('chat-status-text');
            const isOnline = data.status === 'online';

            if (headerDot) headerDot.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
            if (headerText) headerText.textContent = isOnline ? 'Active Now' : `Last seen ${data.last_seen || 'recently'}`;
        }
    },

    onMessagesReadReceipt(data) {
        // Partner has read our sent messages
        if (ChatState.activeChat && ChatState.activeChat.type === 'user' && ChatState.activeChat.id === data.reader_id) {
            document.querySelectorAll('.read-check').forEach(el => {
                el.classList.add('read');
                el.setAttribute('title', 'Read');
            });
        }
    }
};

window.ChatApp = ChatApp;

// ==================== TYPING INDICATOR CONTROLLER ====================

function setupInputListeners() {
    const input = document.getElementById('message-input');
    if (!input) return;

    input.addEventListener('keydown', (e) => {
        // Enter sends message, Shift+Enter makes newline
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
            return;
        }

        // Notify server that user is typing
        if (ChatState.activeChat && !ChatState.isCurrentlyTyping) {
            ChatState.isCurrentlyTyping = true;
            socket.emit('typing_indicator', {
                recipient_type: ChatState.activeChat.type,
                recipient_id: ChatState.activeChat.id,
                is_typing: true
            });
        }

        // Debounce typing stop
        clearTimeout(ChatState.typingTimeout);
        ChatState.typingTimeout = setTimeout(stopTyping, 2000);
    });
}

function stopTyping() {
    if (ChatState.isCurrentlyTyping && ChatState.activeChat) {
        ChatState.isCurrentlyTyping = false;
        socket.emit('typing_indicator', {
            recipient_type: ChatState.activeChat.type,
            recipient_id: ChatState.activeChat.id,
            is_typing: false
        });
    }
}

// ==================== UI HELPERS, MODALS & TABS ====================

function switchSidebarTab(tabName) {
    document.querySelectorAll('.sidebar-tabs .tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    document.querySelectorAll('.conversation-list-container.tab-content').forEach(container => {
        container.classList.toggle('active', container.id === `tab-${tabName}`);
    });

    const label = document.getElementById('tab-section-label');
    if (label) {
        if (tabName === 'direct-chats') label.textContent = 'Direct Messages';
        else if (tabName === 'rooms') label.textContent = 'Chat Rooms';
        else if (tabName === 'directory') label.textContent = 'Community Members';
    }
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('chat-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
    }
}

function refreshActiveChat() {
    if (!ChatState.activeChat) return;
    if (ChatState.activeChat.type === 'user') {
        selectDirectChat(ChatState.activeChat.id, ChatState.activeChat.title, ChatState.activeChat.avatar, ChatState.activeChat.isOnline);
    } else {
        selectRoomChat(ChatState.activeChat.id, ChatState.activeChat.title, ChatState.activeChat.description, ChatState.activeChat.memberCount);
    }
}

function openDefaultRoom() {
    const defIdElem = document.getElementById('default-room-id');
    const roomId = defIdElem ? parseInt(defIdElem.value, 10) : 1;
    selectRoomChat(roomId, 'General', 'Community room for all members', 1);
}

function toggleEmojiDrawer() {
    const drawer = document.getElementById('quick-emoji-drawer');
    if (drawer) drawer.classList.toggle('hidden');
}

function insertEmoji(emoji) {
    const input = document.getElementById('message-input');
    if (!input) return;
    input.value += emoji;
    input.focus();
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('hidden');
}

function openCreateRoomModal() {
    openModal('create-room-modal');
    document.getElementById('new-room-name').focus();
}

function openUsersModal() {
    openModal('users-modal');
    searchUsersModal('');
}

async function handleCreateRoomSubmit(event) {
    event.preventDefault();
    const nameInput = document.getElementById('new-room-name');
    const descInput = document.getElementById('new-room-desc');

    const roomName = nameInput.value.trim();
    const description = descInput.value.trim();

    try {
        const response = await fetch('/api/rooms/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name: roomName, description: description })
        });
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Failed to create room.');
            return;
        }

        closeModal('create-room-modal');
        nameInput.value = '';
        descInput.value = '';

        await loadConversations();
        selectRoomChat(data.room.id, data.room.room_name, data.room.description, data.room.member_count);
    } catch (err) {
        console.error(err);
        alert('An error occurred while creating the room.');
    }
}

async function leaveCurrentRoom() {
    if (!ChatState.activeChat || ChatState.activeChat.type !== 'room') return;
    if (!confirm(`Are you sure you want to leave #${ChatState.activeChat.title}?`)) return;

    const roomId = ChatState.activeChat.id;
    try {
        // Notify socket
        socket.emit('leave_room_event', { room_id: roomId });

        // Call leave API
        await fetch('/api/rooms/leave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_id: roomId })
        });

        // Reset active chat to empty state
        ChatState.activeChat = null;
        document.getElementById('chat-active-panel').classList.add('hidden');
        document.getElementById('chat-empty-state').classList.remove('hidden');

        await loadConversations();
    } catch (err) {
        console.error(err);
    }
}

async function searchUsersModal(query) {
    const list = document.getElementById('modal-user-list');
    if (!list) return;

    try {
        const url = query ? `/api/users?q=${encodeURIComponent(query)}` : '/api/users';
        const res = await fetch(url);
        const users = await res.json();

        if (users.length === 0) {
            list.innerHTML = '<div class="sidebar-empty">No matching users found.</div>';
            return;
        }

        list.innerHTML = users.map(u => `
            <div class="modal-user-item">
                <div class="modal-user-left">
                    <img src="${escapeAttr(u.avatar)}" alt="${escapeAttr(u.username)}">
                    <div>
                        <div class="modal-user-name">${escapeHtml(u.username)}</div>
                        <div class="modal-user-bio">${escapeHtml(u.bio || '')}</div>
                    </div>
                </div>
                <button type="button" class="btn btn-primary btn-sm" 
                    onclick="closeModal('users-modal'); selectDirectChat(${u.id}, '${escapeAttr(u.username)}', '${escapeAttr(u.avatar)}', ${u.is_online})">
                    <i class="fa-solid fa-message"></i> Message
                </button>
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
    }
}

function setupSidebarSearch() {
    const input = document.getElementById('sidebar-search-input');
    const clearBtn = document.getElementById('clear-search-btn');
    if (!input) return;

    input.addEventListener('input', () => {
        const query = input.value.trim().toLowerCase();
        if (query) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }

        // Filter direct chats
        const filteredDirect = ChatState.directChats.filter(c => 
            c.user.username.toLowerCase().includes(query) || 
            (c.last_message && c.last_message.toLowerCase().includes(query))
        );
        renderDirectChatsList(filteredDirect);

        // Filter rooms
        const filteredRooms = ChatState.rooms.filter(r => 
            r.room.room_name.toLowerCase().includes(query) || 
            (r.room.description && r.room.description.toLowerCase().includes(query))
        );
        renderRoomsList(filteredRooms);

        // Filter directory
        loadDirectory(query);
    });

    clearBtn.addEventListener('click', () => {
        input.value = '';
        clearBtn.classList.add('hidden');
        renderDirectChatsList(ChatState.directChats);
        renderRoomsList(ChatState.rooms);
        loadDirectory();
    });
}

// Security HTML escaper to safely render user inputs
function escapeHtml(text) {
    if (!text) return '';
    return text
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeAttr(text) {
    if (!text) return '';
    return text.toString().replace(/"/g, '&quot;');
}
