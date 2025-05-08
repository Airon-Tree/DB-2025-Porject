import requests
from flask import Blueprint, request, jsonify, session
from db import run
from utils import allowed, save_upload
from config import UPLOAD_FOLDER

bp = Blueprint("pins", __name__, url_prefix="/api")


@bp.post("/boards/<int:bid>/pins")
def add_pin(bid):
    uid = session.get("uid")
    if not uid:
        return jsonify(error="unauth"), 401

    tags = request.form.get("tags") or request.json.get("tags", "")
    src = request.form.get("source_url") or request.json.get("source_url", "")
    img_fname = None

    # Case A: file upload
    if "image" in request.files and request.files["image"].filename:
        f = request.files["image"]
        if not allowed(f.filename):
            return jsonify(error="bad type"), 400
        img_fname = save_upload(f)

    # Case B: URL
    elif request.json and request.json.get("image_url"):
        url = request.json["image_url"]
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
        except Exception:
            return jsonify(error="url fetch failed"), 400
        ext = url.split(".")[-1].split("?")[0]
        if ext.lower() not in {"png", "jpg", "jpeg", "gif"}:
            ext = "jpg"
        import uuid, pathlib

        img_fname = f"{uuid.uuid4().hex}.{ext}"
        (UPLOAD_FOLDER / img_fname).write_bytes(r.content)

    else:
        return jsonify(error="no image"), 400

    pin_id = run(
        """INSERT INTO pins (user_id,board_id,tags,source_url)
           VALUES (%s,%s,%s,%s)
           RETURNING pin_id""",
        (uid, bid, tags, src),
        fetchone=True,
        commit=True,
    )["pin_id"]

    # save disk-file path (or blob) into Pictures
    run(
        """INSERT INTO pictures (pin_id, image_blob, uploaded_url)
           VALUES (%s, NULL, %s)""",
        (pin_id, f"/static/uploads/{img_fname}"),
        commit=True,
    )
    pin = {"pin_id": pin_id}

    return jsonify(pin), 201


@bp.get("/boards/<int:bid>/pins")
def list_pins(bid):
    rows = run(
        """SELECT p.pin_id,
                  p.tags AS description,
                  COALESCE(p.source_url,'') AS title,
                  pic.uploaded_url AS image_url
           FROM   pins p
           LEFT JOIN pictures pic ON pic.pin_id = p.pin_id
           WHERE  p.board_id=%s
           ORDER BY p.pin_id DESC""",
        (bid,),
    )
    return jsonify(rows)


@bp.post("/pins/<int:pid>/repin")
def repin(pid):
    uid = session.get("uid")
    target = request.get_json().get("board_id")

    pin = run("""SELECT p.tags AS description,
                p.source_url,
                pic.uploaded_url
        FROM   pins p
        LEFT JOIN pictures pic ON pic.pin_id=p.pin_id
        WHERE  p.pin_id=%s""",
      (pid,), fetchone=True)
    
    if not pin:
        return jsonify(error="not found"), 404
    new_pin_id = run(
        """INSERT INTO pins (user_id,board_id,tags,source_url,original_pin_id)
           VALUES (%s,%s,%s,%s,%s) RETURNING pin_id""",
        (uid, target, pin["description"], pin["source_url"], pid),
        fetchone=True,
        commit=True,
    )["pin_id"]

    # duplicate picture row so new pin_id has its own FK
    run(
        """INSERT INTO pictures (pin_id,image_blob,uploaded_url)
           VALUES (%s,NULL,%s)""",
        (new_pin_id, pin["uploaded_url"]),
        commit=True,
    )
    new_pin = {"pin_id": new_pin_id}

    return jsonify(new_pin), 201


