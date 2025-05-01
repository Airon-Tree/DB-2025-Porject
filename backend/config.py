import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

DB_SETTINGS = dict(
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASS", "djy757911225"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "pin-project"),
)
