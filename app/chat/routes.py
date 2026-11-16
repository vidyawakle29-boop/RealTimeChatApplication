from datetime import datetime, timezone
from flask import render_template, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, desc
from app.extensions import db
from app.models import User, ChatRoom, RoomMember, Message
from app.chat import chat_bp


@chat_bp.route('/')
def index():
    """Landing page introducing the Real-Time Chat platform."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.dashboard'))
    return render_template('index.html')


@chat_bp.route('/dashboard')
@login_required
def dashboard():
    """Main chat application dashboard."""
    # Ensure default room exists
    default_room = ChatRoom.query.filter_by(room_name='General').first()
    if not default_room:
        default_room = ChatRoom(
            room_name='General',
            description='Default community chat room for everyone.',
            created_by=current_user.id
        )
        db.session.add(default_room)
        db.session.commit()

    # Ensure current user is member of default room
    if not default_room.is_member(current_user.id):
        membership = RoomMember(room_id=default_room.id, user_id=current_user.id)
        db.session.add(membership)
        db.session.commit()

    return render_template('dashboard.html', user=current_user, default_room_id=default_room.id)


@chat_bp.route('/api/conversations')
@login_required
def get_conversations():
    """Fetch all active conversations (both 1-to-1 DMs and Rooms) for the sidebar."""
    current_uid = current_user.id

    # 1. Direct Messages: Find all unique partner user IDs
    sent_to = db.session.query(Message.receiver_id).filter(
        Message.sender_id == current_uid,
        Message.receiver_id.isnot(None)
    )
    received_from = db.session.query(Message.sender_id).filter(
        Message.receiver_id == current_uid,
        Message.receiver_id.isnot(None)
    )
    partner_ids = set([r[0] for r in sent_to.union(received_from).all() if r[0]])

    direct_conversations = []
    for pid in partner_ids:
        partner = db.session.get(User, pid)
        if not partner:
            continue

        # Get latest message between current_user and partner
        last_msg = Message.query.filter(
            or_(
                and_(Message.sender_id == current_uid, Message.receiver_id == pid),
                and_(Message.sender_id == pid, Message.receiver_id == current_uid)
            )
        ).order_by(Message.timestamp.desc()).first()

        # Unread messages sent by partner to current user
        unread_count = Message.query.filter_by(
            sender_id=pid,
            receiver_id=current_uid,
            is_read=False
        ).count()

        direct_conversations.append({
            'user': partner.to_dict(),
            'last_message': last_msg.message if last_msg else '',
            'last_message_time': last_msg.timestamp.strftime('%I:%M %p') if last_msg else '',
            'last_message_raw': last_msg.timestamp.isoformat() if last_msg else '',
            'unread_count': unread_count
        })

    # Sort direct conversations by latest message timestamp
    direct_conversations.sort(
        key=lambda x: x['last_message_raw'],
        reverse=True
    )

    # 2. Joined Chat Rooms
    user_memberships = RoomMember.query.filter_by(user_id=current_uid).all()
    room_conversations = []
    for m in user_memberships:
        room = m.room
        if not room:
            continue

        last_room_msg = Message.query.filter_by(room_id=room.id).order_by(Message.timestamp.desc()).first()

        room_conversations.append({
            'room': room.to_dict(current_user_id=current_uid),
            'last_message': f"{last_room_msg.sender.username}: {last_room_msg.message}" if last_room_msg else 'No messages yet.',
            'last_message_time': last_room_msg.timestamp.strftime('%I:%M %p') if last_room_msg else '',
            'last_message_raw': last_room_msg.timestamp.isoformat() if last_room_msg else room.created_at.isoformat()
        })

    room_conversations.sort(
        key=lambda x: x['last_message_raw'],
        reverse=True
    )

    return jsonify({
        'direct': direct_conversations,
        'rooms': room_conversations
    })


@chat_bp.route('/api/users')
@login_required
def get_users():
    """Search and list registered users excluding the current logged-in user."""
    query_str = request.args.get('q', '').strip()
    
    query = User.query.filter(User.id != current_user.id)
    if query_str:
        search_filter = f"%{query_str}%"
        query = query.filter(
            or_(
                User.username.ilike(search_filter),
                User.bio.ilike(search_filter)
            )
        )

    users = query.order_by(User.is_online.desc(), User.username.asc()).limit(50).all()
    return jsonify([u.to_dict() for u in users])


@chat_bp.route('/api/messages/direct/<int:partner_id>')
@login_required
def get_direct_messages(partner_id):
    """Retrieve full chat history between current user and partner, and mark read."""
    partner = db.session.get(User, partner_id)
    if not partner:
        return jsonify({'error': 'User not found'}), 404

    # Query chronological messages between the two users
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == partner_id),
            and_(Message.sender_id == partner_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    # Automatically mark unread incoming messages as read
    unread_messages = Message.query.filter_by(
        sender_id=partner_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()

    if unread_messages:
        for msg in unread_messages:
            msg.is_read = True
        db.session.commit()

    return jsonify({
        'partner': partner.to_dict(),
        'messages': [m.to_dict() for m in messages]
    })


@chat_bp.route('/api/messages/room/<int:room_id>')
@login_required
def get_room_messages(room_id):
    """Retrieve chronological chat history for a specific room."""
    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify({'error': 'Chat room not found'}), 404

    # Optional check: ensure user is member or auto-join public room
    if not room.is_member(current_user.id):
        if not room.is_private:
            # Auto-join public room
            membership = RoomMember(room_id=room.id, user_id=current_user.id)
            db.session.add(membership)
            db.session.commit()
        else:
            return jsonify({'error': 'Unauthorized to view this private room'}), 403

    messages = Message.query.filter_by(room_id=room.id).order_by(Message.timestamp.asc()).all()

    return jsonify({
        'room': room.to_dict(current_user_id=current_user.id),
        'messages': [m.to_dict() for m in messages]
    })


@chat_bp.route('/api/rooms')
@login_required
def list_rooms():
    """List all available public chat rooms with membership flags."""
    query_str = request.args.get('q', '').strip()
    query = ChatRoom.query
    if query_str:
        query = query.filter(ChatRoom.room_name.ilike(f"%{query_str}%"))

    rooms = query.order_by(ChatRoom.created_at.desc()).all()
    return jsonify([r.to_dict(current_user_id=current_user.id) for r in rooms])


@chat_bp.route('/api/rooms/create', methods=['POST'])
@login_required
def create_room():
    """Create a new chat room and add the creator as a member."""
    data = request.get_json() or {}
    room_name = data.get('room_name', '').strip()
    description = data.get('description', '').strip()

    if not room_name or len(room_name) < 3 or len(room_name) > 50:
        return jsonify({'error': 'Room name must be between 3 and 50 characters.'}), 400

    # Ensure unique room name
    if ChatRoom.query.filter_by(room_name=room_name).first():
        return jsonify({'error': f"A room named '{room_name}' already exists."}), 400

    new_room = ChatRoom(
        room_name=room_name,
        description=description,
        created_by=current_user.id,
        is_private=False
    )
    db.session.add(new_room)
    db.session.commit()

    # Creator joins room immediately
    membership = RoomMember(room_id=new_room.id, user_id=current_user.id)
    db.session.add(membership)
    db.session.commit()

    return jsonify({
        'message': 'Room created successfully!',
        'room': new_room.to_dict(current_user_id=current_user.id)
    }), 201


@chat_bp.route('/api/rooms/join', methods=['POST'])
@login_required
def join_room_api():
    """Join an existing chat room."""
    data = request.get_json() or {}
    room_id = data.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id is required'}), 400

    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    if not room.is_member(current_user.id):
        membership = RoomMember(room_id=room.id, user_id=current_user.id)
        db.session.add(membership)
        db.session.commit()

    return jsonify({
        'message': f"Joined room '{room.room_name}'",
        'room': room.to_dict(current_user_id=current_user.id)
    })


@chat_bp.route('/api/rooms/leave', methods=['POST'])
@login_required
def leave_room_api():
    """Leave a chat room."""
    data = request.get_json() or {}
    room_id = data.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id is required'}), 400

    room = db.session.get(ChatRoom, room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404

    membership = RoomMember.query.filter_by(room_id=room.id, user_id=current_user.id).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()

    return jsonify({
        'message': f"Left room '{room.room_name}'",
        'room_id': room_id
    })


@chat_bp.route('/api/messages/mark-read', methods=['POST'])
@login_required
def mark_messages_read():
    """Mark all messages from sender to current user as read."""
    data = request.get_json() or {}
    sender_id = data.get('sender_id')
    if not sender_id:
        return jsonify({'error': 'sender_id is required'}), 400

    unread = Message.query.filter_by(
        sender_id=sender_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()

    for msg in unread:
        msg.is_read = True
    db.session.commit()

    return jsonify({'status': 'success', 'marked_count': len(unread)})
