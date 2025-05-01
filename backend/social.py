from flask import Blueprint, request, jsonify, session
from db import run
from psycopg2 import errors
from sqlalchemy import true

bp = Blueprint("social", __name__, url_prefix="/api")


@bp.post("/pins/<int:pid>/like")
def like(pid):
    uid = session.get("uid")
    try:
        run("INSERT INTO likes (user_id,pin_id) VALUES (%s,%s)", (uid, pid), commit=True)
    except errors.UniqueViolation:
        pass
    return jsonify(message="ok")


@bp.delete("/pins/<int:pid>/like")
def unlike(pid):
    uid = session.get("uid")
    run("DELETE FROM likes WHERE user_id=%s AND pin_id=%s", (uid, pid), commit=True)
    return jsonify(message="ok")


@bp.post("/pins/<int:pid>/comments")
def comment(pid):
    uid = session.get("uid")
    txt = request.get_json()["text"]
    c = run(
        """INSERT INTO comments (user_id,pin_id,comment_text)
           VALUES (%s,%s,%s) RETURNING comment_id,created_at""",
        (uid, pid, txt),
        fetchone=True,
        commit=True,
    )
    return jsonify(c), 201


@bp.get("/pins/<int:pid>/comments")
def list_comments(pid):
    rows = run(
        """SELECT c.comment_id,c.comment_text,c.created_at,
                  u.user_id,u.username
           FROM comments c
           JOIN users u ON c.user_id=u.user_id
           WHERE pin_id=%s ORDER BY c.created_at ASC""",
        (pid,),
    )
    return jsonify(rows)


@bp.post("/boards/<int:bid>/follow")
def follow(bid):
    uid = session.get("uid")
    run(
        "INSERT INTO follows (user_id,board_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (uid, bid),
        commit=True,
    )
    return jsonify(message="followed")


@bp.delete("/boards/<int:bid>/follow")
def unfollow(bid):
    uid = session.get("uid")
    run("DELETE FROM follows WHERE user_id=%s AND board_id=%s", (uid, bid), commit=True)
    return jsonify(message="unfollowed")


@bp.get("/feed")
def feed():
    uid = session.get("uid")
    rows = run(
        """SELECT p.pin_id,p.title,p.image_filename,
                  b.board_id,b.name AS board_name,
                  u.user_id,u.username
           FROM follows f
           JOIN pins p   ON p.board_id=f.board_id
           JOIN boards b ON b.board_id=p.board_id
           JOIN users  u ON u.user_id=p.user_id
           WHERE f.user_id=%s
           ORDER BY p.pin_id DESC
           LIMIT 20""",
        (uid,),
    )
    return jsonify(rows)


@bp.get("/search")
def search():
    q = f"%{request.args.get('q','')}%"
    rows = run(
        """SELECT p.pin_id,p.title,p.description,p.image_filename,
                  b.board_id,b.name AS board_name,
                  u.user_id,u.username
           FROM pins p
           JOIN boards b ON p.board_id=b.board_id
           JOIN users  u ON p.user_id=u.user_id
           WHERE p.title ILIKE %s OR p.description ILIKE %s""",
        (q, q),
    )
    return jsonify(rows)


