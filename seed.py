"""
Seed script to populate initial demo users, chat rooms, and sample messages.
Usage:
    python seed.py
"""

from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models import User, ChatRoom, RoomMember, Message

app = create_app('development')

def seed_database():
    with app.app_context():
        print("🌱 Seeding database with demo data...")
        db.create_all()

        # 1. Create Demo Users
        users_data = [
            {
                'username': 'vidya',
                'email': 'vidya@example.com',
                'bio': 'Software Engineer & Project Creator.',
                'password': 'password123'
            },
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'bio': 'Full-stack developer building real-time apps.',
                'password': 'password123'
            },
            {
                'username': 'bob',
                'email': 'bob@example.com',
                'bio': 'Frontend UI/UX enthusiast & open-source contributor.',
                'password': 'password123'
            },
            {
                'username': 'charlie',
                'email': 'charlie@example.com',
                'bio': 'Python & Flask enthusiast.',
                'password': 'password123'
            }
        ]

        users = {}
        for udata in users_data:
            existing = User.query.filter_by(username=udata['username']).first()
            if not existing:
                user = User(
                    username=udata['username'],
                    email=udata['email'],
                    bio=udata['bio']
                )
                user.set_password(udata['password'])
                db.session.add(user)
                db.session.flush()
                users[udata['username']] = user
                print(f"  + Created user: {udata['username']}")
            else:
                users[udata['username']] = existing

        # 2. Create Chat Rooms
        rooms_data = [
            {
                'room_name': 'General',
                'description': 'Main community lounge for everyone.',
                'creator': users['vidya'].id
            },
            {
                'room_name': 'Tech-Discussion',
                'description': 'Discuss Python, Flask-SocketIO, WebSockets, and architectures.',
                'creator': users['alice'].id
            },
            {
                'room_name': 'Design-Hub',
                'description': 'Modern UI/UX trends, CSS tricks, and animations.',
                'creator': users['bob'].id
            }
        ]

        rooms = {}
        for rdata in rooms_data:
            existing_room = ChatRoom.query.filter_by(room_name=rdata['room_name']).first()
            if not existing_room:
                room = ChatRoom(
                    room_name=rdata['room_name'],
                    description=rdata['description'],
                    created_by=rdata['creator']
                )
                db.session.add(room)
                db.session.flush()
                rooms[rdata['room_name']] = room
                print(f"  + Created room: #{rdata['room_name']}")
            else:
                rooms[rdata['room_name']] = existing_room

        # 3. Add Memberships
        for room in rooms.values():
            for user in users.values():
                if not room.is_member(user.id):
                    m = RoomMember(room_id=room.id, user_id=user.id)
                    db.session.add(m)

        db.session.commit()

        # 4. Add Initial Room Messages if empty
        general_room = rooms.get('General')
        if general_room and Message.query.filter_by(room_id=general_room.id).count() == 0:
            now = datetime.now(timezone.utc)
            m1 = Message(
                sender_id=users['vidya'].id,
                room_id=general_room.id,
                message='Welcome to ChatPulse! The platform is live with Flask-SocketIO WebSockets 🚀',
                timestamp=now - timedelta(minutes=15)
            )
            m2 = Message(
                sender_id=users['alice'].id,
                room_id=general_room.id,
                message='Awesome! Real-time direct messaging and live typing indicators are working smoothly.',
                timestamp=now - timedelta(minutes=10)
            )
            m3 = Message(
                sender_id=users['bob'].id,
                room_id=general_room.id,
                message='Dark mode design and responsive layouts look incredible!',
                timestamp=now - timedelta(minutes=5)
            )
            db.session.add_all([m1, m2, m3])

        # 5. Add Direct Messages between Alice and Bob
        if Message.query.filter_by(sender_id=users['alice'].id, receiver_id=users['bob'].id).count() == 0:
            now = datetime.now(timezone.utc)
            dm1 = Message(
                sender_id=users['alice'].id,
                receiver_id=users['bob'].id,
                message='Hey Bob, did you review the WebSocket connection latency?',
                timestamp=now - timedelta(minutes=20),
                is_read=True
            )
            dm2 = Message(
                sender_id=users['bob'].id,
                receiver_id=users['alice'].id,
                message='Yes Alice! Round-trip time is under 15ms. Looks solid.',
                timestamp=now - timedelta(minutes=18),
                is_read=True
            )
            db.session.add_all([dm1, dm2])

        db.session.commit()
        print("✅ Database seeding completed successfully!")
        print("\nTest Accounts:")
        print("  - Username: vidya   | Password: password123")
        print("  - Username: alice   | Password: password123")
        print("  - Username: bob     | Password: password123")
        print("  - Username: charlie | Password: password123")

if __name__ == '__main__':
    seed_database()
