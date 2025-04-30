import psycopg2, psycopg2.pool
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask import Flask
from db import init_pool, release_conn
from config import UPLOAD_FOLDER
import os


# def create_pool():
#     return psycopg2.pool.SimpleConnectionPool(
#         minconn=1,
#         maxconn=10,
#         user="dbuser",
#         password="dbpass",
#         host="localhost",
#         port=5432,
#         database="pinterest_clone",
#         cursor_factory=RealDictCursor         # every SELECT gives dict rows
#     )

# app = Flask(__name__)
# CORS(app)
# app.config["SECRET_KEY"] = "super-secret"
# pool = create_pool()

# def get_db():
#     if "db" not in g:
#         g.db = pool.getconn()
#     return g.db

# @app.teardown_appcontext
# def close_db(exc):
#     db = g.pop("db", None)
#     if db:
#         pool.putconn(db, close=False)

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "supersecret"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
CORS(app, supports_credentials=True)

init_pool()
app.teardown_appcontext(release_conn)

# blueprints
from auth import bp as auth_bp
from boards import bp as boards_bp
from pins import bp as pins_bp
from social import bp as social_bp

for bp in (auth_bp, boards_bp, pins_bp, social_bp):
    app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(debug=True)

