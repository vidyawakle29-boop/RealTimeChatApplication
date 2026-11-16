from datetime import datetime, timezone
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, ConnectionRefusedError
from app.extensions import db, socketio
from app.models import User, ChatRoom, RoomMember, Message


@socketio.on('connect')
def handle_connect():
    """Handle client connection, authenticate, and register online status."""
    if not current_user.is_authenticated:
        # Reject unauthenticated WebSocket connection
        raise ConnectionRefusedError('Authentication required.')

    current_user.is_online = True
    current_user.last_seen = datetime.now(timezone.utc)
    db.session.commit()

    # Join private personal room for 1-to-1 DMs and personal notifications
    personal_room = f"user_{current_user.id}"
    join_room(personal_room)

    # Join all chat rooms current_user is a member of
    memberships = RoomMember.query.filter_by(user_id=current_user.id).all()
    for m in memberships:
        join_room(f"room_{m.room_id}")

    # Broadcast online status to all other users
    emit('user_status', {
        'user_id': current_user.id,
        'username': current_user.username,
        'status': 'online',
        'avatar': current_user.get_avatar_url(),
        'last_seen': current_user.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')
    }, broadcast=True)

    # Send confirmation back to connecting client
    emit('connected_ack', {
        'message': f"Welcome {current_user.username}! Real-time connection established.",
        'user': current_user.to_dict()
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and broadcast offline status."""
    if current_user.is_authenticated:
        current_user.is_online = False
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

        # Broadcast offline status to all clients
        emit('user_status', {
            'user_id': current_user.id,
            'username': current_user.username,
            'status': 'offline',
            'last_seen': current_user.last_seen.strftime('%I:%M %p')
        }, broadcast=True)


@socketio.on('send_direct_message')
def handle_send_direct_message(data):
    """Handle private 1-to-1 direct messaging."""
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required.'}

    receiver_id = data.get('receiver_id')
    raw_message = data.get('message', '').strip()

    if not receiver_id:
        emit('error_notification', {'message': 'Receiver ID is required.'})
        return {'status': 'error', 'message': 'Receiver ID is required.'}

    if not raw_message:
        emit('error_notification', {'message': 'Message cannot be empty.'})
        return {'status': 'error', 'message': 'Message cannot be empty.'}

    if len(raw_message) > 5000:
        emit('error_notification', {'message': 'Message exceeds 5000 character limit.'})
        return {'status': 'error', 'message': 'Message too long.'}

    receiver = db.session.get(User, int(receiver_id))
    if not receiver:
        emit('error_notification', {'message': 'Recipient user not found.'})
        return {'status': 'error', 'message': 'User not found.'}

    # Persist message to database
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        message=raw_message,
        is_read=False
    )
    db.session.add(new_message)
    db.session.commit()

    msg_payload = new_message.to_dict()

    # Emit to receiver's private room
    emit('new_direct_message', msg_payload, room=f"user_{receiver.id}")

    # Emit to sender's private room (for multiple open tabs / consistency)
    emit('new_direct_message', msg_payload, room=f"user_{current_user.id}")

    # Also emit conversation update to both users for sidebar sync
    conversation_summary = {
        'sender_id': current_user.id,
        'receiver_id': receiver.id,
        'last_message': raw_message,
        'time_display': msg_payload['time_display'],
        'sender_username': current_user.username,
        'receiver_username': receiver.username
    }
    emit('conversation_updated', conversation_summary, room=f"user_{receiver.id}")
    emit('conversation_updated', conversation_summary, room=f"user_{current_user.id}")

    return {'status': 'success', 'message': msg_payload}


@socketio.on('send_room_message')
def handle_send_room_message(data):
    """Handle group chat room messaging."""
    if not current_user.is_authenticated:
        return {'status': 'error', 'message': 'Authentication required.'}

    room_id = data.get('room_id')
    raw_message = data.get('message', '').strip()

    if not room_id:
        emit('error_notification', {'message': 'Room ID is required.'})
        return {'status': 'error', 'message': 'Room ID is required.'}

    if not raw_message:
        emit('error_notification', {'message': 'Message cannot be empty.'})
        return {'status': 'error', 'message': 'Message cannot be empty.'}

    if len(raw_message) > 5000:
        emit('error_notification', {'message': 'Message exceeds 5000 character limit.'})
        return {'status': 'error', 'message': 'Message too long.'}

    room = db.session.get(ChatRoom, int(room_id))
    if not room:
        emit('error_notification', {'message': 'Chat room not found.'})
        return {'status': 'error', 'message': 'Room not found.'}

    # Auto-join user to room if not yet member
    if not room.is_member(current_user.id):
        membership = RoomMember(room_id=room.id, user_id=current_user.id)
        db.session.add(membership)
        db.session.commit()
        join_room(f"room_{room.id}")

    # Persist room message
    new_message = Message(
        sender_id=current_user.id,
        room_id=room.id,
        message=raw_message
    )
    db.session.add(new_message)
    db.session.commit()

    msg_payload = new_message.to_dict()

    # Emit to all members in the room
    emit('new_room_message', msg_payload, room=f"room_{room.id}")

    return {'status': 'success', 'message': msg_payload}


@socketio.on('join_room_event')
def handle_join_room_event(data):
    """Client event to join a chat room WebSocket channel."""
    if not current_user.is_authenticated:
        return

    room_id = data.get('room_id')
    if not room_id:
        return

    room = db.session.get(ChatRoom, int(room_id))
    if not room:
        return

    # Add to DB membership if not already
    if not room.is_member(current_user.id):
        membership = RoomMember(room_id=room.id, user_id=current_user.id)
        db.session.add(membership)
        db.session.commit()

    room_channel = f"room_{room.id}"
    join_room(room_channel)

    # Notify members in the room
    emit('room_notification', {
        'type': 'join',
        'room_id': room.id,
        'room_name': room.room_name,
        'user_id': current_user.id,
        'username': current_user.username,
        'message': f"{current_user.username} joined {room.room_name}.",
        'timestamp': datetime.now(timezone.utc).strftime('%I:%M %p')
    }, room=room_channel)


@socketio.on('leave_room_event')
def handle_leave_room_event(data):
    """Client event to leave a chat room WebSocket channel."""
    if not current_user.is_authenticated:
        return

    room_id = data.get('room_id')
    if not room_id:
        return

    room = db.session.get(ChatRoom, int(room_id))
    if not room:
        return

    room_channel = f"room_{room.id}"

    # Notify members
    emit('room_notification', {
        'type': 'leave',
        'room_id': room.id,
        'room_name': room.room_name,
        'user_id': current_user.id,
        'username': current_user.username,
        'message': f"{current_user.username} left {room.room_name}.",
        'timestamp': datetime.now(timezone.utc).strftime('%I:%M %p')
    }, room=room_channel)

    leave_room(room_channel)


@socketio.on('typing_indicator')
def handle_typing_indicator(data):
    """Handle real-time typing status indicators."""
    if not current_user.is_authenticated:
        return

    recipient_type = data.get('recipient_type')  # 'user' or 'room'
    recipient_id = data.get('recipient_id')
    is_typing = bool(data.get('is_typing', False))

    if not recipient_id or not recipient_type:
        return

    payload = {
        'user_id': current_user.id,
        'username': current_user.username,
        'recipient_type': recipient_type,
        'recipient_id': recipient_id,
        'is_typing': is_typing
    }

    if recipient_type == 'user':
        # Emit typing event to targeted partner
        emit('typing_status', payload, room=f"user_{recipient_id}")
    elif recipient_type == 'room':
        # Emit typing event to all members in room except sender
        emit('typing_status', payload, room=f"room_{recipient_id}", include_self=False)


@socketio.on('mark_read_event')
def handle_mark_read_event(data):
    """Handle mark-as-read real-time receipts."""
    if not current_user.is_authenticated:
        return

    sender_id = data.get('sender_id')
    if not sender_id:
        return

    unread = Message.query.filter_by(
        sender_id=sender_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()

    for m in unread:
        m.is_read = True
    db.session.commit()

    # Inform sender that their messages have been read
    emit('messages_read_receipt', {
        'reader_id': current_user.id,
        'sender_id': sender_id
    }, room=f"user_{sender_id}")
