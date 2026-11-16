import unittest
from app import create_app
from app.extensions import db, socketio
from app.models import User, ChatRoom, RoomMember, Message


class ChatTestCase(unittest.TestCase):
    """Test suite for Chat REST APIs and Real-Time Socket.IO communication."""

    def setUp(self):
        """Set up test app, database, and test clients."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create two test users
        self.u1 = User(username='alice', email='alice@example.com')
        self.u1.set_password('password123')
        self.u2 = User(username='bob', email='bob@example.com')
        self.u2.set_password('password123')
        db.session.add_all([self.u1, self.u2])
        db.session.commit()

        # Create public room
        self.room = ChatRoom(room_name='General', description='General room', created_by=self.u1.id)
        db.session.add(self.room)
        db.session.commit()

        # Add both to room
        db.session.add_all([
            RoomMember(room_id=self.room.id, user_id=self.u1.id),
            RoomMember(room_id=self.room.id, user_id=self.u2.id)
        ])
        db.session.commit()

        self.client1 = self.app.test_client(use_cookies=True)
        self.client2 = self.app.test_client(use_cookies=True)

        # Log in client1 as Alice
        self.client1.post('/auth/login', data={'login_id': 'alice', 'password': 'password123'})
        # Log in client2 as Bob
        self.client2.post('/auth/login', data={'login_id': 'bob', 'password': 'password123'})

    def tearDown(self):
        """Clean up test resources."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ----------------- REST API Tests -----------------

    def test_api_users_search(self):
        """Test searching users excluding self."""
        res = self.client1.get('/api/users?q=bob')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['username'], 'bob')

    def test_api_room_creation_and_membership(self):
        """Test creating a new chat room and auto-joining."""
        res = self.client1.post('/api/rooms/create', json={
            'room_name': 'python-devs',
            'description': 'Channel for Python developers'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['room']['room_name'], 'python-devs')

        # Check DB
        room = ChatRoom.query.filter_by(room_name='python-devs').first()
        self.assertIsNotNone(room)
        self.assertTrue(room.is_member(self.u1.id))

    def test_api_room_join_and_leave(self):
        """Test joining and leaving a chat room via API."""
        new_room = ChatRoom(room_name='gaming', created_by=self.u1.id)
        db.session.add(new_room)
        db.session.commit()

        # Bob joins
        res = self.client2.post('/api/rooms/join', json={'room_id': new_room.id})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(new_room.is_member(self.u2.id))

        # Bob leaves
        res = self.client2.post('/api/rooms/leave', json={'room_id': new_room.id})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(new_room.is_member(self.u2.id))

    def test_api_conversations_and_history(self):
        """Test querying conversation list and message history."""
        # Alice sends message to Bob
        msg = Message(sender_id=self.u1.id, receiver_id=self.u2.id, message='Hello Bob!')
        db.session.add(msg)
        db.session.commit()

        # Alice checks conversations
        res = self.client1.get('/api/conversations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data['direct']), 1)
        self.assertEqual(data['direct'][0]['last_message'], 'Hello Bob!')

        # Bob views message history with Alice
        res2 = self.client2.get(f'/api/messages/direct/{self.u1.id}')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(len(data2['messages']), 1)
        self.assertEqual(data2['messages'][0]['message'], 'Hello Bob!')

        # Verify message marked as read
        updated_msg = db.session.get(Message, msg.id)
        self.assertTrue(updated_msg.is_read)

    # ----------------- Socket.IO Real-Time Tests -----------------

    def test_socket_unauthenticated_connection_rejected(self):
        """Unauthenticated Socket.IO connections must be rejected."""
        unauth_client = self.app.test_client()
        socket_client = socketio.test_client(self.app, flask_test_client=unauth_client)
        self.assertFalse(socket_client.is_connected())

    def test_socket_authenticated_connection(self):
        """Authenticated Socket.IO connection is accepted and emits acknowledgment."""
        socket_client = socketio.test_client(self.app, flask_test_client=self.client1)
        self.assertTrue(socket_client.is_connected())

        received = socket_client.get_received()
        # Should contain connected_ack and user_status
        event_names = [e['name'] for e in received]
        self.assertIn('connected_ack', event_names)
        self.assertIn('user_status', event_names)

        # Verify user is marked online in database
        alice = db.session.get(User, self.u1.id)
        self.assertTrue(alice.is_online)

        socket_client.disconnect()
        # Verify user is marked offline after disconnect
        alice = db.session.get(User, self.u1.id)
        self.assertFalse(alice.is_online)

    def test_socket_direct_message_delivery_and_persistence(self):
        """Test sending 1-to-1 direct message via Socket.IO."""
        socket_alice = socketio.test_client(self.app, flask_test_client=self.client1)
        socket_bob = socketio.test_client(self.app, flask_test_client=self.client2)

        # Clear initial connect events
        socket_alice.get_received()
        socket_bob.get_received()

        # Alice sends direct message to Bob
        socket_alice.emit('send_direct_message', {
            'receiver_id': self.u2.id,
            'message': 'Real-time WebSocket Test Message'
        })

        # Check Bob received new_direct_message
        received_bob = socket_bob.get_received()
        bob_event_names = [e['name'] for e in received_bob]
        self.assertIn('new_direct_message', bob_event_names)

        msg_data = next(e['args'][0] for e in received_bob if e['name'] == 'new_direct_message')
        self.assertEqual(msg_data['message'], 'Real-time WebSocket Test Message')
        self.assertEqual(msg_data['sender_username'], 'alice')

        # Check database persistence
        saved_msg = Message.query.filter_by(
            sender_id=self.u1.id,
            receiver_id=self.u2.id,
            message='Real-time WebSocket Test Message'
        ).first()
        self.assertIsNotNone(saved_msg)

        socket_alice.disconnect()
        socket_bob.disconnect()

    def test_socket_room_message_broadcast(self):
        """Test sending message inside a chat room."""
        socket_alice = socketio.test_client(self.app, flask_test_client=self.client1)
        socket_bob = socketio.test_client(self.app, flask_test_client=self.client2)

        socket_alice.get_received()
        socket_bob.get_received()

        # Alice sends room message
        socket_alice.emit('send_room_message', {
            'room_id': self.room.id,
            'message': 'Hello room members!'
        })

        # Check Bob receives room message
        received_bob = socket_bob.get_received()
        bob_events = [e['name'] for e in received_bob]
        self.assertIn('new_room_message', bob_events)

        room_msg = next(e['args'][0] for e in received_bob if e['name'] == 'new_room_message')
        self.assertEqual(room_msg['message'], 'Hello room members!')
        self.assertEqual(room_msg['room_id'], self.room.id)

        socket_alice.disconnect()
        socket_bob.disconnect()

    def test_socket_typing_indicator(self):
        """Test typing indicator propagation between users."""
        socket_alice = socketio.test_client(self.app, flask_test_client=self.client1)
        socket_bob = socketio.test_client(self.app, flask_test_client=self.client2)

        socket_alice.get_received()
        socket_bob.get_received()

        # Alice begins typing to Bob
        socket_alice.emit('typing_indicator', {
            'recipient_type': 'user',
            'recipient_id': self.u2.id,
            'is_typing': True
        })

        # Bob receives typing status
        received_bob = socket_bob.get_received()
        bob_events = [e['name'] for e in received_bob]
        self.assertIn('typing_status', bob_events)

        typing_data = next(e['args'][0] for e in received_bob if e['name'] == 'typing_status')
        self.assertTrue(typing_data['is_typing'])
        self.assertEqual(typing_data['username'], 'alice')

        socket_alice.disconnect()
        socket_bob.disconnect()


if __name__ == '__main__':
    unittest.main()
