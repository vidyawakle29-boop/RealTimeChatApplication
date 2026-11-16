from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """User account model for authentication and chat identity."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_image = db.Column(db.String(256), nullable=True, default='')
    bio = db.Column(db.String(250), nullable=True, default='Hey there! I am using Real-Time Chat.')
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    sent_messages = db.relationship(
        'Message',
        foreign_keys='Message.sender_id',
        backref='sender',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    received_messages = db.relationship(
        'Message',
        foreign_keys='Message.receiver_id',
        backref='receiver',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    room_memberships = db.relationship(
        'RoomMember',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    created_rooms = db.relationship(
        'ChatRoom',
        backref='creator',
        lazy='dynamic'
    )

    def set_password(self, password: str):
        """Hashes password using secure Werkzeug scrypt/pbkdf2."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def get_avatar_url(self) -> str:
        """Returns custom avatar or generates initials/SVG avatar."""
        if self.profile_image and self.profile_image.strip():
            return self.profile_image
        # High-res clean avatar fallback using ui-avatars
        return f"https://ui-avatars.com/api/?name={self.username}&background=6366f1&color=ffffff&bold=true&rounded=true"

    def to_dict(self, include_email: bool = False) -> dict:
        """Serializes user to dictionary for JSON APIs and Socket payloads."""
        data = {
            'id': self.id,
            'username': self.username,
            'avatar': self.get_avatar_url(),
            'bio': self.bio or '',
            'is_online': bool(self.is_online),
            'last_seen': self.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC') if self.last_seen else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if self.created_at else None
        }
        if include_email:
            data['email'] = self.email
        return data

    def __repr__(self):
        return f"<User {self.username} (ID: {self.id})>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class ChatRoom(db.Model):
    """Chat Room (group channel) model."""
    __tablename__ = 'chat_rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True, default='')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_private = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    members = db.relationship(
        'RoomMember',
        backref='room',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    messages = db.relationship(
        'Message',
        backref='room',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def is_member(self, user_id: int) -> bool:
        """Checks if a user is a member of this room."""
        return self.members.filter_by(user_id=user_id).first() is not None

    def member_count(self) -> int:
        """Returns total member count."""
        return self.members.count()

    def to_dict(self, current_user_id: int = None) -> dict:
        """Serializes room to dictionary."""
        is_joined = False
        if current_user_id:
            is_joined = self.is_member(current_user_id)
        return {
            'id': self.id,
            'room_name': self.room_name,
            'description': self.description or '',
            'created_by': self.created_by,
            'creator_username': self.creator.username if self.creator else 'Unknown',
            'is_private': self.is_private,
            'member_count': self.member_count(),
            'is_member': is_joined,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if self.created_at else None
        }

    def __repr__(self):
        return f"<ChatRoom {self.room_name} (ID: {self.id})>"


class RoomMember(db.Model):
    """Membership table associating users with chat rooms."""
    __tablename__ = 'room_members'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', name='uq_room_user_membership'),
    )

    def __repr__(self):
        return f"<RoomMember User:{self.user_id} in Room:{self.room_id}>"


class Message(db.Model):
    """Chat message model supporting both 1-to-1 DMs and Room messages."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        """Serializes message to dictionary for JSON and Socket.IO emissions."""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_username': self.sender.username if self.sender else 'Unknown',
            'sender_avatar': self.sender.get_avatar_url() if self.sender else '',
            'receiver_id': self.receiver_id,
            'room_id': self.room_id,
            'message': self.message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if self.timestamp else '',
            'time_display': self.timestamp.strftime('%I:%M %p') if self.timestamp else '',
            'date_display': self.timestamp.strftime('%b %d, %Y') if self.timestamp else '',
            'is_read': bool(self.is_read)
        }

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"
