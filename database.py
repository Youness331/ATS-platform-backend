import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(__file__).resolve().parent / "matchline.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                filename TEXT NOT NULL,
                job_description TEXT NOT NULL,
                result_json TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )


def create_analysis(analysis_id: str, filename: str, job_description: str) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    analysis = {
        "analysis_id": analysis_id,
        "status": "queued",
        "filename": filename,
        "job_description": job_description,
        "result": None,
        "created_at": created_at,
        "completed_at": None,
    }
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO analyses
                (analysis_id, status, filename, job_description, result_json, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (analysis_id, "queued", filename, job_description, None, created_at, None),
        )
    return analysis


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM analyses WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()
    return _row_to_analysis(row) if row else None


def list_analyses() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM analyses ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_analysis(row) for row in rows]


def update_status(analysis_id: str, status: str) -> None:
    with _connect() as connection:
        connection.execute(
            "UPDATE analyses SET status = ? WHERE analysis_id = ?",
            (status, analysis_id),
        )


def complete_analysis(analysis_id: str, status: str, result: dict[str, Any]) -> None:
    completed_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE analyses
            SET status = ?, result_json = ?, completed_at = ?
            WHERE analysis_id = ?
            """,
            (status, json.dumps(result), completed_at, analysis_id),
        )


def _row_to_analysis(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "analysis_id": row["analysis_id"],
        "status": row["status"],
        "filename": row["filename"],
        "job_description": row["job_description"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }
