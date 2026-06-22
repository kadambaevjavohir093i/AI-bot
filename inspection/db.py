import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional, List, Dict, Any

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "inspection.db"
UPLOAD_DIR = BASE_DIR / "uploads"
PDF_DIR = BASE_DIR / "pdfs"

UPLOAD_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS inspectors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            telegram_username TEXT,
            telegram_chat_id TEXT UNIQUE,
            registered_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS checklist_sections (
            id INTEGER PRIMARY KEY,
            place_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY,
            section_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            item_type TEXT DEFAULT 'pass_fail',
            require_photo INTEGER DEFAULT 0,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (section_id) REFERENCES checklist_sections(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY,
            place_id INTEGER NOT NULL,
            inspector_name TEXT NOT NULL,
            inspector_telegram_id TEXT DEFAULT '',
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            pdf_path TEXT DEFAULT '',
            drive_url TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            FOREIGN KEY (place_id) REFERENCES places(id)
        );

        CREATE TABLE IF NOT EXISTS inspection_results (
            id INTEGER PRIMARY KEY,
            inspection_id INTEGER NOT NULL,
            checklist_item_id INTEGER NOT NULL,
            result TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            photo_filename TEXT DEFAULT '',
            FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE,
            FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)
        );
        """)


# ── Admin sessions ──────────────────────────────────────────────────────────

def create_session() -> str:
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO admin_sessions (token) VALUES (?)", (token,)
        )
    return token


def session_exists(token: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM admin_sessions WHERE token = ?", (token,)
        ).fetchone()
    return row is not None


def delete_session(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))


# ── Inspectors ──────────────────────────────────────────────────────────────

def upsert_inspector(name: str, telegram_username: str, chat_id: str) -> int:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM inspectors WHERE telegram_chat_id = ?", (chat_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE inspectors SET name = ?, telegram_username = ? WHERE telegram_chat_id = ?",
                (name, telegram_username, chat_id),
            )
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO inspectors (name, telegram_username, telegram_chat_id) VALUES (?, ?, ?)",
            (name, telegram_username, chat_id),
        )
        return cur.lastrowid


def get_inspector_by_chat_id(chat_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM inspectors WHERE telegram_chat_id = ?", (chat_id,)
        ).fetchone()
    return dict(row) if row else None


# ── Places ──────────────────────────────────────────────────────────────────

def list_places() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM places ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_place(place_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM places WHERE id = ?", (place_id,)
        ).fetchone()
    return dict(row) if row else None


def create_place(name: str, description: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO places (name, description) VALUES (?, ?)",
            (name, description),
        )
        return cur.lastrowid


def update_place(place_id: int, name: str, description: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE places SET name = ?, description = ? WHERE id = ?",
            (name, description, place_id),
        )


def delete_place(place_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM places WHERE id = ?", (place_id,))


# ── Sections ────────────────────────────────────────────────────────────────

def get_sections(place_id: int) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist_sections WHERE place_id = ? ORDER BY order_num, id",
            (place_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_section(place_id: int, name: str) -> int:
    with get_conn() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(order_num), -1) FROM checklist_sections WHERE place_id = ?",
            (place_id,),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO checklist_sections (place_id, name, order_num) VALUES (?, ?, ?)",
            (place_id, name, max_order + 1),
        )
        return cur.lastrowid


def delete_section(section_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM checklist_sections WHERE id = ?", (section_id,))


# ── Items ───────────────────────────────────────────────────────────────────

def get_items(section_id: int) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist_items WHERE section_id = ? ORDER BY order_num, id",
            (section_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_items_for_place(place_id: int) -> List[Dict]:
    """Returns items with their section info for building the inspection form."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ci.*, cs.name AS section_name, cs.order_num AS section_order
            FROM checklist_items ci
            JOIN checklist_sections cs ON ci.section_id = cs.id
            WHERE cs.place_id = ?
            ORDER BY cs.order_num, cs.id, ci.order_num, ci.id
            """,
            (place_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_item(section_id: int, name: str, item_type: str, require_photo: bool) -> int:
    with get_conn() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(order_num), -1) FROM checklist_items WHERE section_id = ?",
            (section_id,),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO checklist_items (section_id, name, item_type, require_photo, order_num) VALUES (?, ?, ?, ?, ?)",
            (section_id, name, item_type, 1 if require_photo else 0, max_order + 1),
        )
        return cur.lastrowid


def delete_item(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))


# ── Inspections ─────────────────────────────────────────────────────────────

def create_inspection(place_id: int, inspector_name: str, inspector_telegram_id: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO inspections (place_id, inspector_name, inspector_telegram_id) VALUES (?, ?, ?)",
            (place_id, inspector_name, inspector_telegram_id),
        )
        return cur.lastrowid


def complete_inspection(
    inspection_id: int,
    pdf_path: str = "",
    drive_url: str = "",
    notes: str = "",
) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE inspections
               SET completed_at = datetime('now'), pdf_path = ?, drive_url = ?, notes = ?
               WHERE id = ?""",
            (pdf_path, drive_url, notes, inspection_id),
        )


def get_inspection(inspection_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT i.*, p.name AS place_name
               FROM inspections i
               JOIN places p ON i.place_id = p.id
               WHERE i.id = ?""",
            (inspection_id,),
        ).fetchone()
    return dict(row) if row else None


def list_inspections() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT i.*, p.name AS place_name
               FROM inspections i
               JOIN places p ON i.place_id = p.id
               ORDER BY i.id DESC""",
        ).fetchall()
    return [dict(r) for r in rows]


def save_result(
    inspection_id: int,
    item_id: int,
    result: str,
    detail: str,
    photo_filename: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO inspection_results
               (inspection_id, checklist_item_id, result, detail, photo_filename)
               VALUES (?, ?, ?, ?, ?)""",
            (inspection_id, item_id, result, detail, photo_filename),
        )


def get_results(inspection_id: int) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ir.*, ci.name AS item_name, ci.item_type,
                      cs.name AS section_name, cs.order_num AS section_order,
                      ci.order_num AS item_order
               FROM inspection_results ir
               JOIN checklist_items ci ON ir.checklist_item_id = ci.id
               JOIN checklist_sections cs ON ci.section_id = cs.id
               WHERE ir.inspection_id = ?
               ORDER BY cs.order_num, cs.id, ci.order_num, ci.id""",
            (inspection_id,),
        ).fetchall()
    return [dict(r) for r in rows]
