from flask import Blueprint, render_template, request, redirect, url_for, flash, \
    session, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash
from db import run
from utils import save_upload, allowed
import requests
import os
from config import UPLOAD_FOLDER

# Create a blueprint for all frontend routes
frontend_bp = Blueprint('frontend', __name__)


# Auth check decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('frontend.login'))
        return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


# Helper function to get current user
def get_current_user():
    uid = session.get('uid')
    if not uid:
        return None

    user = run("SELECT user_id, username FROM users WHERE user_id=%s",
               (uid,), fetchone=True)
    return user


# Home page
@frontend_bp.route('/')
def index():
    # Get recent pins for display on homepage
    pins = run(
        """SELECT p.pin_id,
                  COALESCE(p.title,
                      CASE 
                          WHEN p.tags IS NOT NULL AND p.tags != '' 
                              THEN split_part(p.tags, ',', 1)
                          ELSE COALESCE(p.source_url,'')
                      END
                  ) AS title,
                  p.tags AS description,
                  pic.uploaded_url AS image_url,
                  b.board_id, b.name AS board_name,
                  u.user_id, u.username
           FROM pins p
           JOIN boards b ON b.board_id = p.board_id
           JOIN users u ON u.user_id = p.user_id
           LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
           ORDER BY p.created_at DESC
           LIMIT 20"""
    )

    user = get_current_user()
    return render_template('index.html', pins=pins, user=user)


# Login
@frontend_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = run(
            "SELECT user_id, username, password_hash FROM users WHERE email=%s",
            (email,),
            fetchone=True,
        )

        if user and check_password_hash(user["password_hash"], password):
            session['uid'] = user['user_id']
            flash('Successfully logged in!', 'success')
            return redirect(url_for('frontend.index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('auth/login.html')


# Register
@frontend_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Validate inputs
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')

        # Check if username or email already exists
        existing = run(
            "SELECT 1 FROM users WHERE username=%s OR email=%s",
            (username, email),
            fetchone=True,
        )

        if existing:
            flash('Username or email already exists', 'error')
            return render_template('auth/register.html')

        # Create new user
        user = run(
            """INSERT INTO users (username, email, password_hash)
               VALUES (%s, %s, %s)
               RETURNING user_id, username""",
            (username, email, generate_password_hash(password)),
            fetchone=True,
            commit=True,
        )

        session['uid'] = user['user_id']
        flash('Registration successful!', 'success')
        return redirect(url_for('frontend.index'))

    return render_template('auth/register.html')


# Logout
@frontend_bp.route('/logout')
def logout():
    session.pop('uid', None)
    flash('Successfully logged out', 'success')
    return redirect(url_for('frontend.index'))


# User profile
@frontend_bp.route('/users/<int:user_id>')
def user_profile(user_id):
    user = run(
        "SELECT user_id, username, email, created_at FROM users WHERE user_id=%s",
        (user_id,),
        fetchone=True,
    )

    if not user:
        abort(404)

    # Get user's boards
    boards = run(
        "SELECT board_id, name, description FROM boards WHERE user_id=%s",
        (user_id,)
    )

    current_user = get_current_user()

    friendship = None
    if current_user and current_user["user_id"] != user_id:
        friendship = run(
            """SELECT status, requester_id
            FROM friendships
            WHERE (requester_id=%s AND requested_id=%s)
                OR (requester_id=%s AND requested_id=%s)""",
            (current_user["user_id"], user_id, user_id, current_user["user_id"]),
            fetchone=True,
        )



    return render_template('profile/view.html', profile=user, boards=boards,
                           user=current_user, friendship=friendship)


# Board view
@frontend_bp.route('/boards/<int:board_id>')
def view_board(board_id):
    board = run(
        """SELECT b.board_id, b.name, b.description, b.created_at,
                 u.user_id, u.username
          FROM boards b
          JOIN users u ON b.user_id = u.user_id
          WHERE b.board_id=%s""",
        (board_id,),
        fetchone=True,
    )

    if not board:
        abort(404)

        # Get pins for this board
        pins = run(
            """SELECT p.pin_id,
                     COALESCE(p.title,
                         CASE 
                             WHEN p.tags IS NOT NULL AND p.tags != '' 
                                 THEN split_part(p.tags, ',', 1)
                             ELSE COALESCE(p.source_url,'')
                         END
                     ) AS title,
                     p.tags AS description,
                     pic.uploaded_url AS image_url
              FROM pins p
              LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
              WHERE p.board_id=%s
              ORDER BY p.created_at DESC""",
            (board_id,)
        )

    # Check if current user is following this board
    is_following = False
    user = get_current_user()

    if user:
        # Check if user is following this board
        from api.social import default_stream_id
        sid = default_stream_id(user['user_id'])
        follow_status = run(
            "SELECT 1 FROM followstreamboards WHERE stream_id=%s AND board_id=%s",
            (sid, board_id),
            fetchone=True
        )
        is_following = bool(follow_status)

    return render_template('board/view.html', board=board, pins=pins, user=user,
                           is_following=is_following)


# Create new board
@frontend_bp.route('/boards/new', methods=['GET', 'POST'])
@login_required
def create_board():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        if not name:
            flash('Board name is required', 'error')
            return render_template('board/create.html')

        board = run(
            """INSERT INTO boards (user_id, name, description)
               VALUES (%s, %s, %s)
               RETURNING board_id""",
            (session['uid'], name, description),
            fetchone=True,
            commit=True,
        )

        flash('Board created successfully!', 'success')
        return redirect(url_for('frontend.view_board', board_id=board['board_id']))

    user = get_current_user()
    return render_template('board/create.html', user=user)


# Create new pin
@frontend_bp.route('/boards/<int:board_id>/pins/new', methods=['GET', 'POST'])
@login_required
def create_pin(board_id):
    # First check if board exists and belongs to user
    board = run(
        "SELECT board_id, name FROM boards WHERE board_id=%s AND user_id=%s",
        (board_id, session['uid']),
        fetchone=True,
    )

    if not board:
        flash('Board not found or you do not have permission', 'error')
        return redirect(url_for('frontend.index'))

    if request.method == 'POST':
        tags = request.form.get('tags', '')
        source_url = request.form.get('source_url', '')

        # Handle file upload or image URL
        if 'image' in request.files and request.files['image'].filename:
            # File upload
            image_file = request.files['image']
            if not allowed(image_file.filename):
                flash('Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.',
                      'error')
                return render_template('pin/create.html', board=board)

            img_filename = save_upload(image_file)
            image_path = f"/static/uploads/{img_filename}"
        elif source_url:
            # URL provided
            try:
                r = requests.get(source_url, timeout=5)
                r.raise_for_status()

                # Save image from URL
                ext = source_url.split('.')[-1].split('?')[0]
                if ext.lower() not in ['png', 'jpg', 'jpeg', 'gif']:
                    ext = 'jpg'

                import uuid
                img_filename = f"{uuid.uuid4().hex}.{ext}"
                image_path = f"/static/uploads/{img_filename}"

                with open(os.path.join(UPLOAD_FOLDER, img_filename), 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                flash(f'Failed to fetch image from URL: {e}', 'error')
                return render_template('pin/create.html', board=board)
        else:
            flash('Please upload an image or provide an image URL', 'error')
            return render_template('pin/create.html', board=board)

        # Create pin
        pin = run(
            """INSERT INTO pins (user_id, board_id, tags, source_url)
               VALUES (%s, %s, %s, %s)
               RETURNING pin_id""",
            (session['uid'], board_id, tags, source_url),
            fetchone=True,
            commit=True,
        )

        # Save image information
        run(
            """INSERT INTO pictures (pin_id, image_blob, uploaded_url)
               VALUES (%s, NULL, %s)""",
            (pin['pin_id'], image_path),
            commit=True,
        )

        flash('Pin created successfully!', 'success')
        return redirect(url_for('frontend.view_board', board_id=board_id))

    user = get_current_user()
    return render_template('pin/create.html', board=board, user=user)


# View pin details
@frontend_bp.route('/pins/<int:pin_id>')
def view_pin(pin_id):
    pin = run(
        """SELECT p.pin_id, p.tags, p.source_url, p.created_at,
                 pic.uploaded_url AS image_url,
                 b.board_id, b.name AS board_name,
                 u.user_id, u.username
          FROM pins p
          LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
          JOIN boards b ON p.board_id = b.board_id
          JOIN users u ON p.user_id = u.user_id
          WHERE p.pin_id=%s""",
        (pin_id,),
        fetchone=True,
    )

    if not pin:
        abort(404)

    # Get comments for this pin
    comments = run(
        """SELECT c.comment_id, c.comment_text, c.created_at,
                 u.user_id, u.username
          FROM comments c
          JOIN users u ON c.user_id = u.user_id
          WHERE c.pin_id=%s
          ORDER BY c.created_at ASC""",
        (pin_id,)
    )

    # Get like count and check if current user has liked
    likes = run(
        "SELECT COUNT(*) AS like_count FROM likes WHERE pin_id=%s",
        (pin_id,),
        fetchone=True,
    )

    user_liked = False
    user = get_current_user()

    if user:
        liked = run(
            "SELECT 1 FROM likes WHERE user_id=%s AND pin_id=%s",
            (user['user_id'], pin_id),
            fetchone=True,
        )
        user_liked = bool(liked)

        # Get user's boards for repin functionality
        user_boards = run(
            "SELECT board_id, name FROM boards WHERE user_id=%s",
            (user['user_id'],)
        )
    else:
        user_boards = []

    # Check whether current user already follows this board
    is_following = False
    if user:
        from api.social import default_stream_id
        sid = default_stream_id(user["user_id"])
        row = run(
            "SELECT 1 FROM followstreamboards "
            "WHERE stream_id=%s AND board_id=%s",
            (sid, pin["board_id"]),
            fetchone=True,
        )
        is_following = bool(row)

    return render_template(
        'pin/view.html',
        pin=pin,
        comments=comments,
        like_count=likes['like_count'],
        user_liked=user_liked,
        user_boards=user_boards,
        user=user,
        is_following=is_following
    )


# Add comment to pin
@frontend_bp.route('/pins/<int:pin_id>/comment', methods=['POST'])
@login_required
def add_comment(pin_id):
    comment_text = request.form.get('comment_text')

    if not comment_text:
        flash('Comment cannot be empty', 'error')
        return redirect(url_for('frontend.view_pin', pin_id=pin_id))

    run(
        """INSERT INTO comments (user_id, pin_id, comment_text)
           VALUES (%s, %s, %s)""",
        (session['uid'], pin_id, comment_text),
        commit=True,
    )

    flash('Comment added successfully!', 'success')
    return redirect(url_for('frontend.view_pin', pin_id=pin_id))


# Like/unlike pin
@frontend_bp.route('/pins/<int:pin_id>/like', methods=['POST'])
@login_required
def toggle_like(pin_id):
    # Check if already liked
    liked = run(
        "SELECT 1 FROM likes WHERE user_id=%s AND pin_id=%s",
        (session['uid'], pin_id),
        fetchone=True,
    )

    if liked:
        # Unlike
        run(
            "DELETE FROM likes WHERE user_id=%s AND pin_id=%s",
            (session['uid'], pin_id),
            commit=True,
        )
        flash('Pin unliked', 'success')
    else:
        # Like
        run(
            "INSERT INTO likes (user_id, pin_id) VALUES (%s, %s)",
            (session['uid'], pin_id),
            commit=True,
        )
        flash('Pin liked!', 'success')

    return redirect(url_for('frontend.view_pin', pin_id=pin_id))


# Repin
@frontend_bp.route('/pins/<int:pin_id>/repin', methods=['POST'])
@login_required
def repin(pin_id):
    target_board_id = request.form.get('board_id')

    if not target_board_id:
        flash('Please select a board', 'error')
        return redirect(url_for('frontend.view_pin', pin_id=pin_id))

    # Get original pin information
    pin = run(
        """SELECT p.tags, p.source_url, pic.uploaded_url
           FROM pins p
           LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
           WHERE p.pin_id=%s""",
        (pin_id,),
        fetchone=True,
    )

    if not pin:
        flash('Pin not found', 'error')
        return redirect(url_for('frontend.index'))

    # Create repin
    new_pin = run(
        """INSERT INTO pins (user_id, board_id, tags, source_url, original_pin_id)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING pin_id""",
        (session['uid'], target_board_id, pin['tags'], pin['source_url'], pin_id),
        fetchone=True,
        commit=True,
    )

    # Create picture reference
    run(
        """INSERT INTO pictures (pin_id, image_blob, uploaded_url)
           VALUES (%s, NULL, %s)""",
        (new_pin['pin_id'], pin['uploaded_url']),
        commit=True,
    )

    flash('Pin repinned successfully!', 'success')
    return redirect(url_for('frontend.view_board', board_id=target_board_id))


# Follow/unfollow board
@frontend_bp.route('/boards/<int:board_id>/follow', methods=['POST'])
@login_required
def toggle_follow(board_id):
    # Get default follow stream
    from api.social import default_stream_id
    stream_id = default_stream_id(session['uid'])

    # Check if already following
    following = run(
        "SELECT 1 FROM followstreamboards WHERE stream_id=%s AND board_id=%s",
        (stream_id, board_id),
        fetchone=True,
    )

    if following:
        # Unfollow
        run(
            "DELETE FROM followstreamboards WHERE stream_id=%s AND board_id=%s",
            (stream_id, board_id),
            commit=True,
        )
        flash('Board unfollowed', 'success')
    else:
        # Follow
        run(
            "INSERT INTO followstreamboards (stream_id, board_id) VALUES (%s, %s)",
            (stream_id, board_id),
            commit=True,
        )
        flash('Now following board!', 'success')

    return redirect(url_for('frontend.view_board', board_id=board_id))


# Search
@frontend_bp.route('/search')
def search():
    query = request.args.get('q', '')

    if not query:
        return redirect(url_for('frontend.index'))

    # Search for pins
    pins = run(
        """SELECT p.pin_id,
                 COALESCE(p.source_url,'') AS title,
                 p.tags AS description,
                 pic.uploaded_url AS image_url,
                 b.board_id, b.name AS board_name,
                 u.user_id, u.username
          FROM pins p
          JOIN boards b ON b.board_id = p.board_id
          JOIN users u ON p.user_id = u.user_id
          LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
          WHERE p.tags ILIKE %s OR p.source_url ILIKE %s
          ORDER BY p.created_at DESC""",
        (f"%{query}%", f"%{query}%")
    )

    user = get_current_user()
    return render_template('search.html', pins=pins, query=query, user=user)


# User feed (followed boards)
@frontend_bp.route('/feed')
@login_required
def feed():
    pins = run(
        """SELECT p.pin_id,
                 COALESCE(p.source_url,'') AS title,
                 pic.uploaded_url AS image_url,
                 b.board_id, b.name AS board_name,
                 u.user_id, u.username
          FROM followstreams fs
          JOIN followstreamboards fb ON fb.stream_id = fs.stream_id
          JOIN pins p ON p.board_id = fb.board_id
          JOIN boards b ON b.board_id = p.board_id
          JOIN users u ON u.user_id = p.user_id
          LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
          WHERE fs.user_id = %s
          ORDER BY p.created_at DESC
          LIMIT 20""",
        (session['uid'],)
    )

    user = get_current_user()
    return render_template('feed.html', pins=pins, user=user)


# Add friend
@frontend_bp.post("/friends/<int:target_id>/add")
@login_required
def add_friend(target_id):
    # Send a friend‑request from the current user to target
    me = session["uid"]
    if me == target_id:
        flash("You can’t friend yourself 🙃", "error")
        return redirect(url_for("frontend.user_profile", user_id=target_id))

    # If have any relationship?
    rel = run(
        """SELECT friendship_id,status,requester_id
           FROM friendships
           WHERE (requester_id=%s AND requested_id=%s)
              OR (requester_id=%s AND requested_id=%s)""",
        (me, target_id, target_id, me),
        fetchone=True,
    )

    if rel:
        flash("Already requested or friends", "info")
    else:
        run(
            """INSERT INTO friendships (requester_id, requested_id, status)
               VALUES (%s, %s, 'pending')""",
            (me, target_id),
            commit=True,
        )
        flash("Friend request sent 🎉", "success")

    return redirect(url_for("frontend.user_profile", user_id=target_id))


# Remove friend
@frontend_bp.post("/friends/<int:target_id>/remove")
@login_required
def remove_friend(target_id):
    # Delete friendship or pending request between the two users.
    me = session["uid"]
    run(
        """DELETE FROM friendships
           WHERE (requester_id=%s AND requested_id=%s)
              OR (requester_id=%s AND requested_id=%s)""",
        (me, target_id, target_id, me),
        commit=True,
    )
    flash("Friend removed", "success")
    return redirect(url_for("frontend.user_profile", user_id=target_id))

# Three lists on one page: friends , sent requests , received invites
@frontend_bp.route("/friends")
@login_required
def friend_list():
    
    me = session["uid"]

    friends = run(
        """
        SELECT u.user_id, u.username, f.created_at
        FROM   friendships f
        JOIN   users u ON u.user_id = CASE
                                        WHEN f.requester_id=%s
                                        THEN f.requested_id ELSE f.requester_id END
        WHERE  (f.requester_id=%s OR f.requested_id=%s)
          AND  f.status='accepted'
        ORDER  BY u.username
        """,
        (me, me, me),
    )

    sent = run(
        """
        SELECT u.user_id, u.username, f.created_at
        FROM   friendships f
        JOIN   users u ON u.user_id = f.requested_id
        WHERE  f.requester_id=%s AND f.status='pending'
        ORDER  BY f.created_at DESC
        """,
        (me,),
    )

    received = run(
        """
        SELECT u.user_id, u.username, f.created_at, f.friendship_id
        FROM   friendships f
        JOIN   users u ON u.user_id = f.requester_id
        WHERE  f.requested_id=%s AND f.status='pending'
        ORDER  BY f.created_at DESC
        """,
        (me,),
    )

    return render_template(
        "friendlist.html",
        friends=friends,
        sent=sent,
        received=received,
        user=get_current_user(),
    )


# Accept a friend‑request
@frontend_bp.post("/friends/<int:fid>/accept")
@login_required
def accept_friend(fid):

    me = session["uid"]
    run(
        """UPDATE friendships
              SET status = 'accepted'
            WHERE friendship_id = %s
              AND requested_id  = %s
              AND status        = 'pending'""",
        (fid, me),
        commit=True,
    )
    flash("Friend request accepted ✅", "success")
    return redirect(url_for("frontend.friend_list"))
