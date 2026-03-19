"""DB 4 — User Profile queries (with simple base64 'encryption' for demo)."""

import sqlite3
import json
import base64


def _encode(value: str) -> str:
    """Simple base64 encoding to demonstrate encryption concept."""
    return base64.b64encode(value.encode()).decode()


def _decode(value: str) -> str:
    """Decode base64 'encrypted' value."""
    try:
        return base64.b64decode(value.encode()).decode()
    except Exception:
        return value


def save_user_profile(conn: sqlite3.Connection, session_id: str, context: dict):
    """Save or update user profile from extracted context."""
    cursor = conn.cursor()

    # Encode sensitive fields
    medications = _encode(json.dumps(context.get("medications", [])))
    allergies = _encode(json.dumps(context.get("allergies", [])))
    medical_history = _encode(json.dumps(context.get("medical_history", [])))

    cursor.execute("""
        INSERT OR REPLACE INTO user_profiles (session_id, age, sex, medications, allergies, medical_history)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        context.get("age"),
        context.get("sex"),
        medications,
        allergies,
        medical_history,
    ))
    conn.commit()


def get_user_profile(conn: sqlite3.Connection, session_id: str) -> dict | None:
    """Retrieve and decode user profile."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profiles WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()

    if row:
        return {
            "session_id": row["session_id"],
            "age": row["age"],
            "sex": row["sex"],
            "medications": json.loads(_decode(row["medications"])) if row["medications"] else [],
            "allergies": json.loads(_decode(row["allergies"])) if row["allergies"] else [],
            "medical_history": json.loads(_decode(row["medical_history"])) if row["medical_history"] else [],
        }
    return None
