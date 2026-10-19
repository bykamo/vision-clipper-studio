import sqlite3
import os
import json
from contextlib import contextmanager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "vision_clipper.db")

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                mode TEXT NOT NULL,
                num_clips INTEGER NOT NULL,
                status TEXT NOT NULL,
                progress_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_job(video_path: str, mode: str, num_clips: int) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (video_path, mode, num_clips, status, progress_log) VALUES (?, ?, ?, ?, ?)",
            (video_path, mode, num_clips, "pending", json.dumps([]))
        )
        conn.commit()
        return cursor.lastrowid

def update_job_status(job_id: int, status: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()

def append_job_log(job_id: int, log_message: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT progress_log FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            logs = json.loads(row["progress_log"] or "[]")
            logs.append(log_message)
            cursor.execute("UPDATE jobs SET progress_log = ? WHERE id = ?", (json.dumps(logs), job_id))
            conn.commit()

init_db()
