import unittest
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import User, ChatRoom, RoomMember, Message


class ModelsTestCase(unittest.TestCase):
    """Test suite for SQLAlchemy database models."""

    def setUp(self):
        """Set up test application and in-memory database."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up database and tear down context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_password_hashing(self):
        """Test secure password hashing and verification."""
        user = User(username='testuser', email='test@example.com')
        user.set_password('SecretPassword123')

        self.assertIsNotNone(user.password_hash)
        self.assertNotEqual(user.password_hash, 'SecretPassword123')
        self.assertTrue(user.check_password('SecretPassword123'))
        self.assertFalse(user.check_password('WrongPassword'))

    def test_user_to_dict_and_avatar(self):
        """Test user serialization and dynamic avatar generation."""
        user = User(username='johndoe', email='john@example.com', bio='Coding enthusiast')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        self.assertIn('johndoe', user.get_avatar_url())
        user_dict = user.to_dict()
        self.assertEqual(user_dict['username'], 'johndoe')
        self.assertEqual(user_dict['bio'], 'Coding enthusiast')
        self.assertFalse(user_dict['is_online'])

        # Include email check
        user_dict_with_email = user.to_dict(include_email=True)
        self.assertEqual(user_dict_with_email['email'], 'john@example.com')

    def test_chat_room_and_membership(self):
        """Test chat room creation, relationships, and membership queries."""
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password')
        member = User(username='member1', email='member@example.com')
        member.set_password('password')
        db.session.add_all([creator, member])
        db.session.commit()

        room = ChatRoom(room_name='developers', description='Dev channel', created_by=creator.id)
        db.session.add(room)
        db.session.commit()

        # Add member
        m1 = RoomMember(room_id=room.id, user_id=creator.id)
        m2 = RoomMember(room_id=room.id, user_id=member.id)
        db.session.add_all([m1, m2])
        db.session.commit()

        self.assertEqual(room.member_count(), 2)
        self.assertTrue(room.is_member(creator.id))
        self.assertTrue(room.is_member(member.id))

        room_dict = room.to_dict(current_user_id=member.id)
        self.assertEqual(room_dict['room_name'], 'developers')
        self.assertTrue(room_dict['is_member'])

    def test_message_creation_and_to_dict(self):
        """Test message persistence and serialization for DMs and rooms."""
        u1 = User(username='sender', email='sender@example.com')
        u1.set_password('password')
        u2 = User(username='receiver', email='recv@example.com')
        u2.set_password('password')
        db.session.add_all([u1, u2])
        db.session.commit()

        msg = Message(sender_id=u1.id, receiver_id=u2.id, message='Hello there!')
        db.session.add(msg)
        db.session.commit()

        self.assertIsNotNone(msg.id)
        self.assertFalse(msg.is_read)
        self.assertEqual(msg.sender.username, 'sender')
        self.assertEqual(msg.receiver.username, 'receiver')

        msg_dict = msg.to_dict()
        self.assertEqual(msg_dict['message'], 'Hello there!')
        self.assertEqual(msg_dict['sender_username'], 'sender')
        self.assertFalse(msg_dict['is_read'])


if __name__ == '__main__':
    unittest.main()
