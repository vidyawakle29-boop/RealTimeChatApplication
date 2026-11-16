import re
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, ChatRoom, RoomMember
from app.auth import auth_bp

# Regex patterns for input validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration with strict validation."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        errors = []
        if not username or not USERNAME_REGEX.match(username):
            errors.append('Username must be 3-30 characters long and contain only letters, numbers, and underscores.')

        if not email or not EMAIL_REGEX.match(email):
            errors.append('Please provide a valid email address.')

        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        # Check uniqueness
        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append(f"Username '{username}' is already taken.")
            if User.query.filter_by(email=email).first():
                errors.append(f"Email '{email}' is already registered.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('register.html', username=username, email=email), 400

        # Create new user
        new_user = User(
            username=username,
            email=email,
            bio='Excited to connect on Real-Time Chat!'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-join default "General" room if it exists or create it
        general_room = ChatRoom.query.filter_by(room_name='General').first()
        if not general_room:
            general_room = ChatRoom(
                room_name='General',
                description='Public room for all community members.',
                created_by=new_user.id
            )
            db.session.add(general_room)
            db.session.commit()

        # Join the room
        membership = RoomMember(room_id=general_room.id, user_id=new_user.id)
        db.session.add(membership)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login via username or email."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_id or not password:
            flash('Please enter your username/email and password.', 'danger')
            return render_template('login.html', login_id=login_id), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id.lower())
        ).first()

        if user and user.check_password(password):
            user.last_seen = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('chat.dashboard'))
        else:
            flash('Invalid username/email or password. Please try again.', 'danger')
            return render_template('login.html', login_id=login_id), 401

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out current authenticated user."""
    current_user.is_online = False
    current_user.last_seen = datetime.now(timezone.utc)
    db.session.commit()
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and update user profile settings."""
    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()
        profile_image = request.form.get('profile_image', '').strip()

        if len(bio) > 250:
            flash('Bio cannot exceed 250 characters.', 'danger')
            return render_template('profile.html', user=current_user), 400

        current_user.bio = bio
        if profile_image:
            current_user.profile_image = profile_image
        else:
            current_user.profile_image = ''

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    # Load statistics
    joined_rooms_count = RoomMember.query.filter_by(user_id=current_user.id).count()
    sent_msgs_count = current_user.sent_messages.count()

    return render_template(
        'profile.html',
        user=current_user,
        joined_rooms_count=joined_rooms_count,
        sent_msgs_count=sent_msgs_count
    )


@auth_bp.route('/api/check-username')
def check_username():
    """Quick asynchronous check for username availability."""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({'available': False, 'message': 'Username cannot be blank.'})
    
    if not USERNAME_REGEX.match(username):
        return jsonify({'available': False, 'message': 'Invalid format. Use 3-30 letters/numbers/underscores.'})

    existing = User.query.filter_by(username=username).first()
    return jsonify({
        'available': existing is None,
        'message': 'Username is available' if existing is None else 'Username is already taken'
    })
