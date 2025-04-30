from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import run

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/signup")
def signup():
    data = request.get_json()
    username, email, pwd = data["username"], data["email"], data["password"]
    try:
        user = run(
            """INSERT INTO users (username,email,password_hash)
               VALUES (%s,%s,%s)
               RETURNING user_id,username""",
            (username, email, generate_password_hash(pwd)),
            fetchone=True,
            commit=True,
        )
    except Exception:
        return jsonify(error="username or email already exists"), 400
    return jsonify(user), 201


@bp.post("/login")
def login():
    data = request.get_json()
    user = run(
        "SELECT user_id,username,password_hash FROM users WHERE email=%s",
        (data["email"],),
        fetchone=True,
    )
    if not user or not check_password_hash(user["password_hash"], data["password"]):
        return jsonify(error="bad credentials"), 401
    session["uid"] = user["user_id"]
    return jsonify({"id": user["user_id"], "username": user["username"]})

