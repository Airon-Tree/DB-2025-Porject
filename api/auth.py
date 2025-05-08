from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import run
from psycopg2 import errors

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/signup")
def signup():
    data = request.get_json()

    # First check if we even received JSON data
    if not data:
        return {"error": "No JSON data received"}, 400

    try:
        username = data["username"].strip()
        email = data["email"].strip().lower()
        pwd = data["password"]

        # Validate that all required fields have values
        if not username:
            return {"error": "Username cannot be empty"}, 400
        if not email:
            return {"error": "Email cannot be empty"}, 400
        if not pwd:
            return {"error": "Password cannot be empty"}, 400

    except KeyError as e:
        # Be specific about which field is missing
        missing_field = str(e).strip("'")
        return {"error": f"Missing required field: {missing_field}"}, 400

    try:
        user = run(
            """INSERT INTO users (username,email,password_hash)
               VALUES (%s,%s,%s)
               RETURNING user_id,username""",
            (username, email, generate_password_hash(pwd)),
            fetchone=True,
            commit=True,
        )
        # Successfully created user
        return jsonify({"user_id": user["user_id"], "username": user["username"]}), 201

    except errors.UniqueViolation as e:
        # More detailed unique violation error
        if "username" in str(e):
            return {"error": "Username already exists"}, 409
        elif "email" in str(e):
            return {"error": "Email already exists"}, 409
        else:
            return {"error": "Username or email already exists"}, 409

    except Exception as e:
        # More detailed error logging and response
        import logging, traceback
        logging.error("Signup failed: %s\n%s", e, traceback.format_exc())

        # More user-friendly error message
        error_msg = str(e).split("\n")[0]
        return {"error": f"Database error: {error_msg}"}, 500


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


@bp.get("/me")
def me():
    uid = session.get("uid")
    if not uid:
        return {"error": "unauth"}, 401
    user = run("SELECT user_id, username FROM users WHERE user_id=%s",
               (uid,), fetchone=True)
    return user