import requests
from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, \
    render_template
from db import run
from utils import allowed, save_upload
from config import UPLOAD_FOLDER
import re, uuid, os
from urllib.parse import urlparse

bp = Blueprint("pins", __name__, url_prefix="/api")


@bp.route("/boards/<int:board_id>/pins/new", methods=["GET", "POST"])
def create_pin(board_id):
    user = get_user()
    board = run("SELECT * FROM boards WHERE board_id = %s", (board_id,), fetchone=True)

    if not board:
        flash("Board not found", "error")
        return redirect(url_for("frontend.index"))

    if request.method == "POST":
        title = request.form.get("title", "")
        tags = request.form.get("tags", "")
        source_url = request.form.get("source_url", "")
        img_fname = None

        # Generate a title if not provided
        if not title:
            if tags:
                # Use first tag as title
                title = tags.split(',')[0].strip().capitalize()
            elif source_url:
                # Extract domain for title
                domain_match = re.search(r'^(?:https?:\/\/)?(?:www\.)?([^\/]+)',
                                         source_url)
                if domain_match:
                    title = f"Pin from {domain_match.group(1)}"
                else:
                    title = "Untitled Pin"
            else:
                title = "Untitled Pin"

        try:
            # Handle uploaded image file
            if "image" in request.files and request.files["image"].filename:
                f = request.files["image"]
                if not allowed(f.filename):
                    flash("File type not allowed", "error")
                    return render_template("pin/create.html", board=board, user=user)
                img_fname = save_upload(f)

            # If no file uploaded, attempt download from URL
            elif source_url:
                # Fix imgur gallery URLs
                if 'imgur.com/gallery' in source_url or 'imgur.com/a/' in source_url:
                    # Try to extract the image ID using regex
                    match = re.search(r'([a-zA-Z0-9]{5,8})', source_url.split('/')[-1])
                    if match:
                        img_id = match.group(1)
                        source_url = f'https://i.imgur.com/{img_id}.jpg'

                # Add headers to avoid rate limiting
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                # Try to fetch the image with a timeout
                try:
                    r = requests.get(source_url, timeout=10, headers=headers)
                    r.raise_for_status()
                except requests.exceptions.HTTPError as http_err:
                    if r.status_code == 429:
                        flash(
                            f"Failed to fetch image: Too many requests. Please try again later or use a different URL.",
                            "error")
                    else:
                        flash(
                            f"Failed to fetch image: {r.status_code} error. Please check the URL and try again.",
                            "error")
                    return render_template("pin/create.html", board=board, user=user)
                except requests.exceptions.RequestException as req_err:
                    flash(
                        f"Failed to fetch image: {str(req_err)}. Please check the URL and try again.",
                        "error")
                    return render_template("pin/create.html", board=board, user=user)

                # Improved extension parsing for complex URLs
                try:
                    # First check Content-Type for image type
                    content_type = r.headers.get('Content-Type', '')
                    if content_type.startswith('image/'):
                        # Use content type to determine extension
                        if 'image/jpeg' in content_type:
                            ext = 'jpg'
                        elif 'image/png' in content_type:
                            ext = 'png'
                        elif 'image/gif' in content_type:
                            ext = 'gif'
                        elif 'image/webp' in content_type:
                            ext = 'webp'
                        else:
                            # Try to get from URL as fallback
                            parsed_url = urlparse(source_url)
                            path = parsed_url.path
                            if '.' in path:
                                url_ext = path.split('.')[-1].split('?')[0].lower()
                                if url_ext in {"png", "jpg", "jpeg", "gif", "webp"}:
                                    ext = 'jpg' if url_ext == 'jpeg' else url_ext
                                else:
                                    ext = 'jpg'  # Default if extension not recognized
                            else:
                                ext = 'jpg'  # Default if no extension in URL
                    else:
                        # Not an image content type, try to get extension from URL
                        parsed_url = urlparse(source_url)
                        path = parsed_url.path
                        if '.' in path:
                            url_ext = path.split('.')[-1].split('?')[0].lower()
                            if url_ext in {"png", "jpg", "jpeg", "gif", "webp"}:
                                ext = 'jpg' if url_ext == 'jpeg' else url_ext
                            else:
                                flash(
                                    "URL does not appear to point to an image. Please use a direct image URL.",
                                    "error")
                                return render_template("pin/create.html", board=board,
                                                       user=user)
                        else:
                            # No extension and not an image content type
                            flash(
                                "URL does not appear to point to an image. Please use a direct image URL.",
                                "error")
                            return render_template("pin/create.html", board=board,
                                                   user=user)
                except Exception:
                    # Default to jpg on any error determining extension
                    ext = 'jpg'

                img_fname = f"{uuid.uuid4().hex}.{ext}"

                try:
                    with open(os.path.join(app.config['UPLOAD_FOLDER'], img_fname),
                              "wb") as f:
                        f.write(r.content)
                except Exception as save_err:
                    flash(f"Failed to save image: {str(save_err)}", "error")
                    return render_template("pin/create.html", board=board, user=user)
            else:
                flash("Please provide an image", "error")
                return render_template("pin/create.html", board=board, user=user)

            # Insert new pin with title — auto-incrementing pin_id
            pin = run(
                """
                INSERT INTO pins (user_id, board_id, title, tags, source_url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING pin_id
                """,
                (user["user_id"], board_id, title, tags, source_url),
                fetchone=True,
                commit=True
            )

            # Link image to the pin
            run(
                """
                INSERT INTO pictures (pin_id, image_blob, uploaded_url)
                VALUES (%s, NULL, %s)
                """,
                (pin["pin_id"], f"/static/uploads/{img_fname}"),
                commit=True
            )

            flash("Pin created successfully", "success")
            return redirect(url_for("frontend.view_board", board_id=board_id))

        except Exception as e:
            print(f"Error creating pin: {str(e)}")
            flash("An error occurred while creating your pin. Please try again later.",
                  "error")
            return render_template("pin/create.html", board=board, user=user)

    return render_template("pin/create.html", board=board, user=user)


@bp.get("/boards/<int:bid>/pins")
def list_pins(bid):
    rows = run(
        """SELECT p.pin_id,
                  p.tags AS description,
                  COALESCE(p.title, 
                           CASE 
                             WHEN p.tags IS NOT NULL AND p.tags != '' THEN 
                               SPLIT_PART(p.tags, ',', 1)
                             ELSE COALESCE(p.source_url, 'Untitled Pin')
                           END) AS title,
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

    pin = run("""SELECT p.title,
                p.tags AS description,
                p.source_url,
                pic.uploaded_url
        FROM   pins p
        LEFT JOIN pictures pic ON pic.pin_id=p.pin_id
        WHERE  p.pin_id=%s""",
              (pid,), fetchone=True)

    if not pin:
        return jsonify(error="not found"), 404

    # If no title in original pin, generate one from tags or source_url
    title = pin.get("title")
    if not title:
        if pin.get("description"):
            title = pin["description"].split(',')[0].strip().capitalize()
        elif pin.get("source_url"):
            domain_match = re.search(r'^(?:https?:\/\/)?(?:www\.)?([^\/]+)',
                                     pin["source_url"])
            if domain_match:
                title = f"Pin from {domain_match.group(1)}"
            else:
                title = "Untitled Pin"
        else:
            title = "Untitled Pin"

    new_pin_id = run(
        """INSERT INTO pins (user_id, board_id, title, tags, source_url, original_pin_id)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING pin_id""",
        (uid, target, title, pin["description"], pin["source_url"], pid),
        fetchone=True,
        commit=True,
    )["pin_id"]

    # duplicate picture row so new pin_id has its own FK
    run(
        """INSERT INTO pictures (pin_id, image_blob, uploaded_url)
           VALUES (%s, NULL, %s)""",
        (new_pin_id, pin["uploaded_url"]),
        commit=True,
    )
    new_pin = {"pin_id": new_pin_id}

    return jsonify(new_pin), 201