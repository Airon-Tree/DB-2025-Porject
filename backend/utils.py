import os, uuid
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_upload(file_storage) -> str:
    """Returns **filename** saved under static/uploads/."""
    fname = secure_filename(f"{uuid.uuid4().hex}_{file_storage.filename}")
    path = UPLOAD_FOLDER / fname
    file_storage.save(path)
    return fname

