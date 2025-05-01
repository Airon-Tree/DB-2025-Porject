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

    title = request.form.get("title") or request.json.get("title", "")
    desc = request.form.get("description") or request.json.get("description", "")
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

    pin = run(
        """INSERT INTO pins (user_id,board_id,title,description,image_filename)
           VALUES (%s,%s,%s,%s,%s)
           RETURNING pin_id""",
        (uid, bid, title, desc, img_fname),
        fetchone=True,
        commit=True,
    )
    return jsonify(pin), 201


@bp.get("/boards/<int:bid>/pins")
def list_pins(bid):
    rows = run(
        """SELECT pin_id,title,description,image_filename
           FROM pins WHERE board_id=%s ORDER BY pin_id DESC""",
        (bid,),
    )
    return jsonify(rows)


@bp.post("/pins/<int:pid>/repin")
def repin(pid):
    uid = session.get("uid")
    target = request.get_json().get("board_id")
    pin = run("SELECT title,description,image_filename FROM pins WHERE pin_id=%s", (pid,), fetchone=True)
    if not pin:
        return jsonify(error="not found"), 404
    new_pin = run(
        """INSERT INTO pins (user_id,board_id,title,description,image_filename,original_pin_id)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING pin_id""",
        (uid, target, pin["title"], pin["description"], pin["image_filename"], pid),
        fetchone=True,
        commit=True,
    )
    return jsonify(new_pin), 201


