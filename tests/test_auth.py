import unittest
from app import create_app
from app.extensions import db
from app.models import User, ChatRoom, RoomMember


class AuthTestCase(unittest.TestCase):
    """Test suite for User Authentication and Account Management."""

    def setUp(self):
        """Set up test app and client."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        """Tear down database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_success(self):
        """Test successful user registration and auto-joining General room."""
        response = self.client.post('/auth/register', data={
            'username': 'john_doe',
            'email': 'john@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        # Verify user in database
        user = User.query.filter_by(username='john_doe').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('password123'))

        # Verify General room membership
        general_room = ChatRoom.query.filter_by(room_name='General').first()
        self.assertIsNotNone(general_room)
        self.assertTrue(general_room.is_member(user.id))

    def test_registration_validation_errors(self):
        """Test that invalid username, email, or passwords are rejected."""
        # Short username
        res = self.client.post('/auth/register', data={
            'username': 'ab',
            'email': 'valid@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'Username must be 3-30 characters', res.data)

        # Invalid email
        res = self.client.post('/auth/register', data={
            'username': 'validuser',
            'email': 'invalid-email-address',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'valid email address', res.data)

        # Password mismatch
        res = self.client.post('/auth/register', data={
            'username': 'validuser',
            'email': 'valid@example.com',
            'password': 'password123',
            'confirm_password': 'different_password'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'Passwords do not match', res.data)

    def test_duplicate_user_prevention(self):
        """Test prevention of duplicate usernames and emails."""
        existing_user = User(username='existing_user', email='existing@example.com')
        existing_user.set_password('password123')
        db.session.add(existing_user)
        db.session.commit()

        # Attempt duplicate username
        res = self.client.post('/auth/register', data={
            'username': 'existing_user',
            'email': 'new@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'already taken', res.data)

        # Attempt duplicate email
        res = self.client.post('/auth/register', data={
            'username': 'unique_user',
            'email': 'existing@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'already registered', res.data)

    def test_login_and_logout(self):
        """Test authentication flow, session establishment, and logout."""
        user = User(username='chatuser', email='chat@example.com')
        user.set_password('Secret123')
        db.session.add(user)
        db.session.commit()

        # Login with wrong password
        res = self.client.post('/auth/login', data={
            'login_id': 'chatuser',
            'password': 'WrongPassword'
        })
        self.assertEqual(res.status_code, 401)

        # Login with correct username
        res = self.client.post('/auth/login', data={
            'login_id': 'chatuser',
            'password': 'Secret123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome back, chatuser', res.data)

        # Logout
        res = self.client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'logged out safely', res.data)

    def test_protected_routes(self):
        """Ensure protected routes redirect unauthenticated visitors."""
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/auth/login', res.headers['Location'])

        res = self.client.get('/auth/profile')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/auth/login', res.headers['Location'])

    def test_profile_update(self):
        """Test updating user profile bio and settings."""
        user = User(username='profileuser', email='profile@example.com')
        user.set_password('Secret123')
        db.session.add(user)
        db.session.commit()

        # Login
        self.client.post('/auth/login', data={'login_id': 'profileuser', 'password': 'Secret123'})

        # Update profile
        res = self.client.post('/auth/profile', data={
            'bio': 'Updated test bio!',
            'profile_image': 'https://example.com/avatar.png'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Profile updated successfully', res.data)

        updated = db.session.get(User, user.id)
        self.assertEqual(updated.bio, 'Updated test bio!')
        self.assertEqual(updated.profile_image, 'https://example.com/avatar.png')


if __name__ == '__main__':
    unittest.main()
