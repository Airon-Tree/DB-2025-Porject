from flask import Blueprint, request, jsonify, session
from db import run
from psycopg2 import errors
# from sqlalchemy import true

bp = Blueprint("social", __name__, url_prefix="/api")


def default_stream_id(uid: int) -> int:
    """Return the stream_id for the user’s default follow stream,
       creating it the first time."""
    row = run(
        "SELECT stream_id FROM followstreams "
        "WHERE user_id=%s AND name='__default__'", (uid,), fetchone=True
    )
    if row:
        return row["stream_id"]

    # create and return
    return run(
        "INSERT INTO followstreams (user_id,name) "
        "VALUES (%s,'__default__') RETURNING stream_id",
        (uid,), fetchone=True, commit=True
    )["stream_id"]

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
    sid = default_stream_id(uid)
    run(
        "INSERT INTO followstreamboards (stream_id,board_id) "
        "VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (sid, bid),
        commit=True,
    )
    return jsonify(message="followed")


@bp.delete("/boards/<int:bid>/follow")
def unfollow(bid):
    uid = session.get("uid")
    sid = default_stream_id(uid)      
    run("DELETE FROM followstreamboards WHERE stream_id=%s AND board_id=%s",
        (sid, bid), commit=True)
    return jsonify(message="unfollowed")


@bp.get("/feed")
def feed():
    uid = session.get("uid")
    rows = run(
        """SELECT p.pin_id,
                  COALESCE(p.source_url,'')       AS title,
                  pic.uploaded_url                AS image_url,
                  b.board_id,b.name AS board_name,
                  u.user_id,u.username
           FROM followstreams fs
           JOIN followstreamboards fb ON fb.stream_id = fs.stream_id
           JOIN pins p ON p.board_id = fb.board_id
           JOIN boards b ON b.board_id = p.board_id
           JOIN users  u ON u.user_id = p.user_id
           LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
           WHERE fs.user_id = %s
           ORDER BY p.pin_id DESC
           LIMIT 20""",
        (uid,),
    )
    return jsonify(rows)

@bp.get("/boards/<int:bid>/is_following")
def is_following(bid):
    uid = session.get("uid")
    sid = default_stream_id(uid)
    row = run("SELECT 1 FROM followstreamboards WHERE stream_id=%s AND board_id=%s",
              (sid, bid), fetchone=True)
    return {"following": bool(row)}


@bp.get("/search")
def search():
    q = f"%{request.args.get('q','')}%"
    rows = run(
        """SELECT p.pin_id,
                  COALESCE(p.source_url,'')   AS title,
                  p.tags                      AS description,
                  pic.uploaded_url            AS image_url,
                  b.board_id, b.name AS board_name,
                  u.user_id, u.username
           FROM   pins p
           JOIN   boards   b   ON b.board_id = p.board_id
           JOIN   users    u   ON u.user_id  = p.user_id
           LEFT   JOIN pictures pic ON pic.pin_id = p.pin_id
           WHERE  p.tags       ILIKE %s
              OR  p.source_url ILIKE %s""",
        (q, q),
    )
    return jsonify(rows)


