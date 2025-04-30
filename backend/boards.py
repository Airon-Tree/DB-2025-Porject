from flask import Blueprint, request, jsonify, session
from db import run

bp = Blueprint("boards", __name__, url_prefix="/api")


@bp.post("/boards")
def create_board():
    uid = session.get("uid")
    if not uid:
        return jsonify(error="unauth"), 401
    body = request.get_json()
    board = run(
        """INSERT INTO boards (user_id,name,description)
           VALUES (%s,%s,%s)
           RETURNING board_id,name,description""",
        (uid, body["name"], body.get("description", "")),
        fetchone=True,
        commit=True,
    )
    return jsonify(board), 201


@bp.get("/users/<int:uid>/boards")
def list_boards(uid):
    rows = run("SELECT board_id,name,description FROM boards WHERE user_id=%s", (uid,))
    return jsonify(rows)

