from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import run
from psycopg2 import errors

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/signup")
def signup():
    data = request.get_json()

    try:
        username = data["username"].strip()
        email    = data["email"].strip().lower()
        pwd      = data["password"]
        assert username and email and pwd
    except (KeyError, AssertionError):
        return {"error": "missing fields"}, 400

    try:
        user = run(
            """INSERT INTO users (username,email,password_hash)
               VALUES (%s,%s,%s)
               RETURNING user_id,username""",
            (username, email, generate_password_hash(pwd)),
            fetchone=True,
            commit=True,
        )
        return user, 201
    # except Exception:
    #     return jsonify(error="username or email already exists"), 400
    

    except errors.UniqueViolation:
        # somebody else already took the username or email
        return {"error": "username OR email already exists"}, 409

    except Exception as e:
        # log and surface the real DB error
        import logging, traceback
        logging.error("signup failed: %s\n%s", e, traceback.format_exc())
        return {"error": str(e).split("\n")[0]}, 500      # quick dev aid


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

