from flask import Flask, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask.cli import with_appcontext
import os
import click
from werkzeug.security import generate_password_hash
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, static_folder="static")

    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY='supersecret',
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', 'static/uploads'),
    )

    # Override config with test config if passed
    if test_config is not None:
        app.config.update(test_config)

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize CORS with explicit configuration for API routes
    CORS(app,
         resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True)

    # Initialize database connection
    from db import init_pool, release_conn

    # Set environment variables for database connection
    os.environ['DB_NAME'] = os.environ.get('DB_NAME', 'pinboards')
    os.environ['DB_USER'] = os.environ.get('DB_USER', 'postgres')
    os.environ['DB_PASSWORD'] = os.environ.get('DB_PASSWORD', 'root')
    os.environ['DB_HOST'] = os.environ.get('DB_HOST', 'localhost')
    os.environ['DB_PORT'] = os.environ.get('DB_PORT', '5432')

    # Initialize the connection pool without arguments
    init_pool()
    app.teardown_appcontext(release_conn)

    # Register CLI commands
    register_cli_commands(app)

    # Import API blueprints
    from api.auth import bp as auth_bp
    from api.boards import bp as boards_bp
    from api.pins import bp as pins_bp
    from api.social import bp as social_bp

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(boards_bp)
    app.register_blueprint(pins_bp)
    app.register_blueprint(social_bp)

    # Import and register frontend routes
    from routes import frontend_bp
    app.register_blueprint(frontend_bp)

    # Add error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error="Server error"), 500

    return app


@click.command('init-db')
@click.option('--drop', is_flag=True,
              help='Drop all existing tables before creating new ones')
@with_appcontext
def init_db_command(drop):
    """Initialize the database tables."""
    from db import get_conn
    conn = get_conn()
    cursor = conn.cursor()

    try:
        if drop:
            print("Dropping all existing tables...")
            # Drop tables in correct order to handle foreign key constraints
            cursor.execute("""
                DROP TABLE IF EXISTS Comments CASCADE;
                DROP TABLE IF EXISTS Likes CASCADE;
                DROP TABLE IF EXISTS FollowStreamBoards CASCADE;
                DROP TABLE IF EXISTS FollowStreams CASCADE;
                DROP TABLE IF EXISTS Friendships CASCADE;
                DROP TABLE IF EXISTS Pictures CASCADE;
                DROP TABLE IF EXISTS Pins CASCADE;
                DROP TABLE IF EXISTS Boards CASCADE;
                DROP TABLE IF EXISTS Users CASCADE;
            """)
            print("All tables dropped successfully!")

        # Create tables
        print("Creating tables...")
        create_tables_sql = """
        -- Users Table
        CREATE TABLE IF NOT EXISTS Users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Boards Table
        CREATE TABLE IF NOT EXISTS Boards (
            board_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );

        -- Pins Table
        CREATE TABLE IF NOT EXISTS Pins (
            pin_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            board_id INT NOT NULL,
            original_pin_id INT,
            title VARCHAR(255) NOT NULL,
            tags TEXT,
            source_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (board_id) REFERENCES Boards(board_id) ON DELETE CASCADE,
            FOREIGN KEY (original_pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
        );

        -- Pictures Table
        CREATE TABLE IF NOT EXISTS Pictures (
            pin_id INT PRIMARY KEY,
            image_blob BYTEA,
            original_url VARCHAR(255),
            uploaded_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
        );

        -- Friendships Table
        CREATE TABLE IF NOT EXISTS Friendships (
            friendship_id SERIAL PRIMARY KEY,
            requester_id INT NOT NULL,
            requested_id INT NOT NULL,
            status VARCHAR(10) NOT NULL CHECK (status IN ('pending', 'accepted', 'declined')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (requester_id, requested_id),
            FOREIGN KEY (requester_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (requested_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );

        -- FollowStreams Table
        CREATE TABLE IF NOT EXISTS FollowStreams (
            stream_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );

        -- FollowStreamBoards Table
        CREATE TABLE IF NOT EXISTS FollowStreamBoards (
            stream_id INT NOT NULL,
            board_id INT NOT NULL,
            PRIMARY KEY (stream_id, board_id),
            FOREIGN KEY (stream_id) REFERENCES FollowStreams(stream_id) ON DELETE CASCADE,
            FOREIGN KEY (board_id) REFERENCES Boards(board_id) ON DELETE CASCADE
        );

        -- Likes Table
        CREATE TABLE IF NOT EXISTS Likes (
            like_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            pin_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, pin_id),
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
        );

        -- Comments Table
        CREATE TABLE IF NOT EXISTS Comments (
            comment_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            pin_id INT NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
        );
        """

        cursor.execute(create_tables_sql)

        conn.commit()
        print("Database initialization completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
    finally:
        cursor.close()


@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Insert test data into the database."""
    from db import get_conn
    conn = get_conn()
    cursor = conn.cursor()

    try:
        print("Inserting test data...")

        # 1. Users (omit user_id)
        users_data = [
            ('erica', 'erica@example.com', generate_password_hash('hash_erica')),
            ('timmy', 'timmy@example.com', generate_password_hash('hash_timmy')),
            ('alice', 'alice@example.com', generate_password_hash('hash_alice')),
            ('bob', 'bob@example.com', generate_password_hash('hash_bob')),
            ('charlie', 'charlie@example.com', generate_password_hash('hash_charlie'))
        ]
        execute_values(
            cursor,
            "INSERT INTO Users (username, email, password_hash) VALUES %s",
            users_data,
            template="(%s, %s, %s)"
        )

        # 2. Boards (omit board_id)
        boards_data = [
            (1, 'Furniture', 'Antique & modern pieces'),
            (1, 'Dream Vacations', 'Beaches and hidden gems'),
            (2, 'Super Dinosaurs', 'Everything T-Rex & friends'),
            (2, 'Pirates', 'Arrr! Ships, maps, treasure'),
            (3, 'Monsters', 'Creepy-cute creatures'),
            (4, 'Tech', 'Latest tech innovations'),
            (5, 'Nature Photography', 'Stunning landscapes and wildlife')
        ]
        execute_values(
            cursor,
            "INSERT INTO Boards (user_id, name, description) VALUES %s",
            boards_data,
            template="(%s, %s, %s)"
        )

        # 3. Pins with titles
        cursor.execute("""
            INSERT INTO Pins (user_id, board_id, title, tags, source_url, created_at) VALUES
            (1, 1, 'Modern Brown Couch', 'couch,brown,modern', 'https://example.com/sofa.jpg', CURRENT_TIMESTAMP),
            (1, 2, 'Beautiful Beach', 'beach,sand,sea', 'https://example.com/beach.jpg', CURRENT_TIMESTAMP),
            (2, 3, 'T-Rex Dinosaur', 'dinosaur,trex', 'https://example.com/trex.png', CURRENT_TIMESTAMP),
            (2, 4, 'Pirate Ship', 'pirate,ship', 'https://example.com/pirate.png', CURRENT_TIMESTAMP),
            (3, 5, 'Cute Monster', 'monster,cute', 'https://example.com/cute_monster.jpg', CURRENT_TIMESTAMP),
            (1, 2, 'Alpine Mountains', 'mountain,alpine', 'https://example.com/alps.jpg', CURRENT_TIMESTAMP),
            (4, 6, 'New Smartphone', 'phone,gadget', 'https://example.com/new_phone.png', CURRENT_TIMESTAMP),
            (5, 7, 'Forest Sunrise', 'forest,sunrise', 'https://example.com/forest_sunrise.jpg', CURRENT_TIMESTAMP)
        """)

        # 4. Repins with titles
        cursor.execute("""
            INSERT INTO Pins (user_id, board_id, title, original_pin_id, created_at) VALUES
            (2, 4, 'Beautiful Beach', 2, CURRENT_TIMESTAMP),
            (3, 5, 'T-Rex Dinosaur', 3, CURRENT_TIMESTAMP),
            (5, 7, 'Beautiful Beach', 2, CURRENT_TIMESTAMP),
            (4, 6, 'T-Rex Dinosaur', 3, CURRENT_TIMESTAMP)
        """)

        # 5. Pictures (omit pin_id here only if you're adding AFTER pins are inserted & fetched)
        cursor.execute("""
            INSERT INTO Pictures (pin_id, image_blob, original_url, uploaded_url, created_at) VALUES
            (1, '\\xDEADBEEF', 'https://example.com/sofa.jpg', NULL, CURRENT_TIMESTAMP),
            (2, '\\xDEADBEEF', 'https://example.com/beach.jpg', NULL, CURRENT_TIMESTAMP),
            (3, '\\xDEADBEEF', 'https://example.com/trex.png', NULL, CURRENT_TIMESTAMP),
            (4, '\\xDEADBEEF', 'https://example.com/pirate.png', NULL, CURRENT_TIMESTAMP),
            (7, '\\xDEADBEEF', 'https://example.com/cute_monster.jpg', NULL, CURRENT_TIMESTAMP),
            (8, '\\xDEADBEEF', 'https://example.com/alps.jpg', NULL, CURRENT_TIMESTAMP),
            (9, '\\xDEADBEEF', 'https://example.com/new_phone.png', NULL, CURRENT_TIMESTAMP),
            (10, '\\xDEADBEEF', 'https://example.com/forest_sunrise.jpg', NULL, CURRENT_TIMESTAMP)
        """)

        # 6. Friendships (omit friendship_id)
        cursor.execute("""
            INSERT INTO Friendships (requester_id, requested_id, status) VALUES
            (1, 2, 'accepted'),
            (2, 3, 'accepted'),
            (3, 4, 'accepted'),
            (5, 1, 'pending')
        """)

        # 7. Follow Streams (omit stream_id)
        cursor.execute(
            "INSERT INTO FollowStreams (user_id, name) VALUES (2, 'Monsters and Dinosaurs')"
        )
        cursor.execute("""
            INSERT INTO FollowStreamBoards (stream_id, board_id) VALUES
            (1, 3), (1, 5), (1, 1), (1, 2)
        """)
        cursor.execute(
            "INSERT INTO FollowStreams (user_id, name) VALUES (3, 'Design & Nature')"
        )
        cursor.execute("""
            INSERT INTO FollowStreamBoards (stream_id, board_id) VALUES
            (2, 1), (2, 7)
        """)

        # 8. Likes (omit like_id)
        cursor.execute("""
            INSERT INTO Likes (user_id, pin_id) VALUES
            (2, 1),
            (1, 3),
            (3, 2),
            (4, 7),
            (5, 8),
            (1, 10)
        """)

        # 9. Comments (omit comment_id)
        cursor.execute("""
            INSERT INTO Comments (user_id, pin_id, comment_text) VALUES
            (2, 1, 'Cute couch!'),
            (1, 3, 'Awesome picture!'),
            (5, 8, 'Cool picture of the alps'),
            (4, 3, 'Amazing t-rex.'),
            (3, 10, 'Wish I was there')
        """)

        # Sync sequences
        cursor.execute("SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users))")
        cursor.execute("SELECT setval('boards_board_id_seq', (SELECT MAX(board_id) FROM boards))")
        cursor.execute("SELECT setval('pins_pin_id_seq', (SELECT MAX(pin_id) FROM pins))")
        cursor.execute("SELECT setval('friendships_friendship_id_seq', (SELECT MAX(friendship_id) FROM friendships))")
        cursor.execute("SELECT setval('followstreams_stream_id_seq', (SELECT MAX(stream_id) FROM followstreams))")
        cursor.execute("SELECT setval('likes_like_id_seq', (SELECT MAX(like_id) FROM likes))")
        cursor.execute("SELECT setval('comments_comment_id_seq', (SELECT MAX(comment_id) FROM comments))")

        conn.commit()
        print("Test data inserted successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Error inserting test data: {e}")
    finally:
        cursor.close()



def register_cli_commands(app):
    """Register database functions with the Flask app."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)  # Add the new seed-db command


# This block is only executed when running this file directly
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)