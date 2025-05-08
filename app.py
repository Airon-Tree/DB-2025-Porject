from flask import Flask, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask.cli import with_appcontext
import os
import click
from werkzeug.security import generate_password_hash
from psycopg2.extras import execute_values  # Make sure to add this import



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
         resources={r"/api/*": {"origins": "http://localhost:3000"}},
         supports_credentials=True)

    # Initialize database
    from db import init_pool, release_conn
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

        # 1. Users
        users_data = [
            (1, 'erica', 'erica@example.com', generate_password_hash('hash_erica')),
            (2, 'timmy', 'timmy@example.com', generate_password_hash('hash_timmy')),
            (3, 'alice', 'alice@example.com', generate_password_hash('hash_alice')),
            (4, 'bob', 'bob@example.com', generate_password_hash('hash_bob')),
            (
            5, 'charlie', 'charlie@example.com', generate_password_hash('hash_charlie'))
        ]
        execute_values(
            cursor,
            "INSERT INTO Users (user_id, username, email, password_hash) VALUES %s",
            users_data,
            template="(%s, %s, %s, %s)"
        )

        # 2. Boards
        boards_data = [
            (1, 1, 'Furniture', 'Antique & modern pieces'),
            (2, 1, 'Dream Vacations', 'Beaches and hidden gems'),
            (3, 2, 'Super Dinosaurs', 'Everything T-Rex & friends'),
            (4, 2, 'Pirates', 'Arrr! Ships, maps, treasure'),
            (5, 3, 'Monsters', 'Creepy-cute creatures'),
            (6, 4, 'Tech', 'Latest tech innovations'),
            (7, 5, 'Nature Photography', 'Stunning landscapes and wildlife')
        ]
        execute_values(
            cursor,
            "INSERT INTO Boards (board_id, user_id, name, description) VALUES %s",
            boards_data,
            template="(%s, %s, %s, %s)"
        )

        # 3. Original Pins - Using raw SQL for CURRENT_TIMESTAMP
        cursor.execute("""
            INSERT INTO Pins (pin_id, user_id, board_id, tags, source_url, created_at) VALUES
            (1, 1, 1, 'couch,brown,modern', 'https://example.com/sofa.jpg', CURRENT_TIMESTAMP),
            (2, 1, 2, 'beach,sand,sea', 'https://example.com/beach.jpg', CURRENT_TIMESTAMP),
            (3, 2, 3, 'dinosaur,trex', 'https://example.com/trex.png', CURRENT_TIMESTAMP),
            (4, 2, 4, 'pirate,ship', 'https://example.com/pirate.png', CURRENT_TIMESTAMP),
            (7, 3, 5, 'monster,cute', 'https://example.com/cute_monster.jpg', CURRENT_TIMESTAMP),
            (8, 1, 2, 'mountain,alpine', 'https://example.com/alps.jpg', CURRENT_TIMESTAMP),
            (9, 4, 6, 'phone,gadget', 'https://example.com/new_phone.png', CURRENT_TIMESTAMP),
            (10, 5, 7, 'forest,sunrise', 'https://example.com/forest_sunrise.jpg', CURRENT_TIMESTAMP)
        """)

        # Repins - Using raw SQL for CURRENT_TIMESTAMP
        cursor.execute("""
            INSERT INTO Pins (pin_id, user_id, board_id, original_pin_id, created_at) VALUES
            (5, 2, 4, 2, CURRENT_TIMESTAMP),  -- Timmy repins Erica's beach to Pirates
            (6, 3, 5, 3, CURRENT_TIMESTAMP),  -- Alice repins Timmy's dinosaur to Monsters
            (11, 5, 7, 2, CURRENT_TIMESTAMP), -- Charlie repins Erica's beach to Nature Photography
            (12, 4, 6, 3, CURRENT_TIMESTAMP)  -- Bob repins Timmy's dinosaur to Tech Gadgets
        """)

        # 4. Pictures - Using raw SQL for CURRENT_TIMESTAMP
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

        # 5. Friendships
        cursor.execute("""
            INSERT INTO Friendships (friendship_id, requester_id, requested_id, status) VALUES
            (1, 1, 2, 'accepted'), -- Erica ↔ Timmy
            (2, 2, 3, 'accepted'), -- Timmy → Alice
            (3, 3, 4, 'accepted'), -- Alice ↔ Bob
            (4, 5, 1, 'pending')   -- Charlie → Erica (still pending)
        """)

        # 6. Follow Streams
        cursor.execute(
            "INSERT INTO FollowStreams (stream_id, user_id, name) VALUES (1, 2, 'Monsters and Dinosaurs')")

        cursor.execute("""
            INSERT INTO FollowStreamBoards (stream_id, board_id) VALUES
            (1, 3), (1, 5), (1, 1), (1, 2)
        """)

        cursor.execute(
            "INSERT INTO FollowStreams (stream_id, user_id, name) VALUES (2, 3, 'Design & Nature')")

        cursor.execute("""
            INSERT INTO FollowStreamBoards (stream_id, board_id) VALUES
            (2, 1), (2, 7)
        """)

        # 7. Likes
        cursor.execute("""
            INSERT INTO Likes (like_id, user_id, pin_id) VALUES
            (1, 2, 1), -- Timmy like Erica's sofa
            (2, 1, 3), -- Erica like Timmy's dinosaur
            (3, 3, 2), -- Alice like Erica's beach
            (4, 4, 7), -- Bob like Alice's monster
            (5, 5, 8), -- Charlie like Erica's alps
            (6, 1, 10)  -- Erica like Charlie's forest sunrise
        """)

        # 8. Comments
        cursor.execute("""
            INSERT INTO Comments (comment_id, user_id, pin_id, comment_text) VALUES
            (1, 2, 1, 'Cute couch!'),
            (2, 1, 3, 'Awesome picture!'),
            (3, 5, 8, 'Cool picture of the alps'),
            (4, 4, 3, 'Amazing t-rex.'),
            (5, 3, 10, 'Wish I was there')
        """)

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


def reset_all_sequences():
    """Reset all sequences in the database to start after the highest existing ID."""
    from db import run

    tables_with_sequences = [
        ('users', 'user_id'),
        ('boards', 'board_id'),
        ('pins', 'pin_id'),
        ('friendships', 'friendship_id'),
        ('followstreams', 'stream_id'),
        ('likes', 'like_id'),
        ('comments', 'comment_id')
    ]

    for table, id_column in tables_with_sequences:
        try:
            # Get the current maximum ID
            result = run(f"SELECT MAX({id_column}) FROM {table}")
            max_id = result[0][0] if result and result[0][0] else 0

            # Reset the sequence to start after the maximum ID
            sequence_name = f"{table}_{id_column}_seq"
            run(f"ALTER SEQUENCE {sequence_name} RESTART WITH {max_id + 1}",
                commit=True)
            print(f"Reset {sequence_name} to start at {max_id + 1}")
        except Exception as e:
            print(f"Error resetting sequence for {table}.{id_column}: {e}")

# This block is only executed when running this file directly
if __name__ == "__main__":
    app = create_app()
    reset_all_sequence()
    app.run(debug=True, host='0.0.0.0', port=5000)