import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Make sure to create a DB called pinboards first in pgAdmin

# Connect to PostgreSQL using environment variables
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432")
)
conn.autocommit = False
cursor = conn.cursor()
try:
    # SQL to create all tables
    create_tables_sql = """
    -- Users Table
    CREATE TABLE Users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Boards Table
    CREATE TABLE Boards (
        board_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    );

    -- Pins Table
    CREATE TABLE Pins (
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
    CREATE TABLE Pictures (
        pin_id INT PRIMARY KEY,
        image_blob BYTEA NOT NULL,
        original_url VARCHAR(255),
        uploaded_url VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
    );

    -- Friendships Table
    CREATE TABLE Friendships (
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
    CREATE TABLE FollowStreams (
        stream_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    );

    -- FollowStreamBoards Table
    CREATE TABLE FollowStreamBoards (
        stream_id INT NOT NULL,
        board_id INT NOT NULL,
        PRIMARY KEY (stream_id, board_id),
        FOREIGN KEY (stream_id) REFERENCES FollowStreams(stream_id) ON DELETE CASCADE,
        FOREIGN KEY (board_id) REFERENCES Boards(board_id) ON DELETE CASCADE
    );

    -- Likes Table
    CREATE TABLE Likes (
        like_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        pin_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, pin_id),
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
    );

    -- Comments Table
    CREATE TABLE Comments (
        comment_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        pin_id INT NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (pin_id) REFERENCES Pins(pin_id) ON DELETE CASCADE
    );
    """

    # Execute the SQL
    cursor.execute(create_tables_sql)

    # Commit the transaction
    conn.commit()
    print("All tables created successfully!")

except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
try:
    # 1. Users
    users_data = [
        (1, 'erica', 'erica@example.com', 'hash_erica'),
        (2, 'timmy', 'timmy@example.com', 'hash_timmy'),
        (3, 'alice', 'alice@example.com', 'hash_alice'),
        (4, 'bob', 'bob@example.com', 'hash_bob'),
        (5, 'charlie', 'charlie@example.com', 'hash_charlie')
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

    # Commit the transaction
    conn.commit()
    print("All data inserted successfully!")

except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
finally:
    # Close the cursor and connection
    cursor.close()
    conn.close()