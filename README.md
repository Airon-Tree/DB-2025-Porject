# Pinterest Clone

A Flask-based Pinterest clone application for showcasing and sharing visual content.

## Description

This project is a Pinterest-inspired web application built with Flask and PostgreSQL. It allows users to create boards, pin images, follow other users, and interact with content through comments and likes.

## Features

- User authentication and account management
- Create and manage boards to organize pins
- Upload and pin images with descriptions and tags
- Repin content from other users
- Friend connections and social features
- Follow specific boards through custom streams
- Like and comment on pins
- Responsive design for both desktop and mobile

## Technologies

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Flask's built-in session management with password hashing

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pinterest-clone
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Initialize the database:
   ```bash
   flask init-db
   ```

5. (Optional) Seed the database with sample data:
   ```bash
   flask seed-db
   ```

6. Run the application:
   ```bash
   flask run
   ```

7. Visit http://localhost:5000 in your browser.

## Project Structure

```
pinterest-clone/
├── api/               # API endpoints
│   ├── auth.py        # Authentication routes
│   ├── boards.py      # Board management
│   ├── pins.py        # Pin management
│   └── social.py      # Social features (follows, likes, comments)
├── static/            # Static assets
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript files
│   └── uploads/       # User uploaded content
├── templates/         # Jinja2 templates
├── db.py              # Database connection management
├── routes.py          # Frontend routes
├── __init__.py        # Application factory
└── pyproject.toml     # Project configuration
```

## Development

### Database Initialization

The application includes CLI commands for database management:

```bash
# Create database tables
flask init-db

# Drop and recreate all tables
flask init-db --drop

# Insert sample data
flask seed-db
```

### API Endpoints

The API is organized into the following blueprints:

- `/api/auth/` - User authentication and registration
- `/api/boards/` - Board creation, modification, and deletion
- `/api/pins/` - Pin creation, modification, and deletion
- `/api/social/` - Friend requests, follows, likes, and comments

## License

[MIT License](LICENSE)

## Acknowledgements

This project was created as part of the DB-2025 course.