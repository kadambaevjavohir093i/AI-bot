"""FastAPI inspection web application."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Cookie, FastAPI, Form, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, drive, tg
from .db import UPLOAD_DIR, PDF_DIR
from .pdf_gen import generate_pdf

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Inspection App")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

db.init_db()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _admin_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _is_admin(session_token: Optional[str]) -> bool:
    if not session_token:
        return False
    return db.session_exists(session_token)


def _save_photo(upload: Optional[UploadFile]) -> str:
    """Save uploaded photo and return its filename (or empty string)."""
    if upload is None or not upload.filename:
        return ""
    ext = Path(upload.filename).suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename
    content = upload.file.read()
    if not content:
        return ""
    path.write_bytes(content)
    return filename


# ── Home ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Annotated[Optional[str], Cookie()] = None):
    places = db.list_places()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "places": places, "is_admin": _is_admin(session)},
    )


# ── Inspection flow ───────────────────────────────────────────────────────────

@app.get("/inspect/{place_id}", response_class=HTMLResponse)
async def inspect_start(request: Request, place_id: int):
    place = db.get_place(place_id)
    if not place:
        return HTMLResponse("Place not found", status_code=404)
    items = db.get_all_items_for_place(place_id)
    if not items:
        return HTMLResponse(
            "This place has no checklist items yet. Ask an admin to add them.",
            status_code=400,
        )

    # Group items by section for template
    sections: dict = {}
    section_order: list = []
    for item in items:
        sec = item["section_name"]
        if sec not in sections:
            sections[sec] = []
            section_order.append(sec)
        sections[sec].append(item)

    return templates.TemplateResponse(
        "inspect.html",
        {
            "request": request,
            "place": place,
            "sections": sections,
            "section_order": section_order,
            "company_name": config.COMPANY_NAME,
        },
    )


@app.post("/inspect/{place_id}/submit")
async def inspect_submit(
    request: Request,
    place_id: int,
):
    place = db.get_place(place_id)
    if not place:
        return HTMLResponse("Place not found", status_code=404)

    form = await request.form()
    inspector_name = str(form.get("inspector_name", "")).strip()
    inspector_telegram = str(form.get("inspector_telegram", "")).strip()

    if not inspector_name:
        return HTMLResponse("Inspector name is required", status_code=400)

    # Create inspection record
    inspection_id = db.create_inspection(place_id, inspector_name, inspector_telegram)

    items = db.get_all_items_for_place(place_id)
    for item in items:
        item_id = item["id"]
        result = str(form.get(f"result_{item_id}", "")).strip()
        detail = str(form.get(f"detail_{item_id}", "")).strip()

        # Handle photo upload
        photo_file = form.get(f"photo_{item_id}")
        photo_filename = ""
        if photo_file and hasattr(photo_file, "filename") and photo_file.filename:
            content = await photo_file.read()
            if content:
                ext = Path(photo_file.filename).suffix.lower() or ".jpg"
                fname = f"{uuid.uuid4().hex}{ext}"
                (UPLOAD_DIR / fname).write_bytes(content)
                photo_filename = fname

        db.save_result(inspection_id, item_id, result, detail, photo_filename)

    notes = str(form.get("notes", "")).strip()

    # Generate PDF
    inspection = db.get_inspection(inspection_id)
    results = db.get_results(inspection_id)
    pdf_path = generate_pdf(inspection, place, results, config.COMPANY_NAME)

    # Upload to Google Drive
    drive_url = drive.upload_pdf(
        pdf_path,
        f"inspection_{place['name']}_{inspection_id}.pdf",
    )

    # Complete the inspection record
    db.complete_inspection(inspection_id, str(pdf_path), drive_url or "", notes)

    # Re-fetch with completed_at set
    inspection = db.get_inspection(inspection_id)

    # Send via Telegram (async)
    await tg.notify_inspection(pdf_path, inspection, place, drive_url)

    return RedirectResponse(f"/done/{inspection_id}", status_code=303)


@app.get("/done/{inspection_id}", response_class=HTMLResponse)
async def done(request: Request, inspection_id: int):
    inspection = db.get_inspection(inspection_id)
    if not inspection:
        return HTMLResponse("Inspection not found", status_code=404)
    return templates.TemplateResponse(
        "done.html",
        {"request": request, "inspection": inspection},
    )


@app.get("/done/{inspection_id}/pdf")
async def download_pdf(inspection_id: int):
    inspection = db.get_inspection(inspection_id)
    if not inspection or not inspection.get("pdf_path"):
        return HTMLResponse("PDF not found", status_code=404)
    pdf_path = Path(inspection["pdf_path"])
    if not pdf_path.exists():
        return HTMLResponse("PDF file missing", status_code=404)
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"inspection_{inspection_id}.pdf",
    )


# ── Admin auth ────────────────────────────────────────────────────────────────

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, session: Annotated[Optional[str], Cookie()] = None):
    if _is_admin(session):
        return RedirectResponse("/admin")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/admin/login")
async def admin_login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    if (
        username == config.ADMIN_USERNAME
        and _admin_hash(password) == _admin_hash(config.ADMIN_PASSWORD)
    ):
        token = db.create_session()
        resp = RedirectResponse("/admin", status_code=303)
        resp.set_cookie("session", token, httponly=True, max_age=86400 * 7)
        return resp
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
        status_code=401,
    )


@app.get("/admin/logout")
async def admin_logout(session: Annotated[Optional[str], Cookie()] = None):
    if session:
        db.delete_session(session)
    resp = RedirectResponse("/")
    resp.delete_cookie("session")
    return resp


# ── Admin dashboard ───────────────────────────────────────────────────────────

def _require_admin(session: Optional[str]) -> Optional[RedirectResponse]:
    if not _is_admin(session):
        return RedirectResponse("/admin/login")
    return None


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    session: Annotated[Optional[str], Cookie()] = None,
):
    redir = _require_admin(session)
    if redir:
        return redir
    places = db.list_places()
    inspections = db.list_inspections()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "places": places, "inspections": inspections},
    )


# ── Place management ──────────────────────────────────────────────────────────

@app.get("/admin/places/new", response_class=HTMLResponse)
async def new_place_form(
    request: Request,
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    return templates.TemplateResponse(
        "admin/place_form.html",
        {"request": request, "place": None, "error": None},
    )


@app.post("/admin/places/new")
async def create_place(
    request: Request,
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            "admin/place_form.html",
            {"request": request, "place": None, "error": "Name is required"},
        )
    place_id = db.create_place(name, description.strip())
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


@app.get("/admin/places/{place_id}", response_class=HTMLResponse)
async def place_detail(
    request: Request,
    place_id: int,
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    place = db.get_place(place_id)
    if not place:
        return HTMLResponse("Place not found", status_code=404)
    sections = db.get_sections(place_id)
    sections_with_items = [(sec, db.get_items(sec["id"])) for sec in sections]
    return templates.TemplateResponse(
        "admin/place_detail.html",
        {
            "request": request,
            "place": place,
            "sections_with_items": sections_with_items,
        },
    )


@app.post("/admin/places/{place_id}/edit")
async def edit_place(
    request: Request,
    place_id: int,
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    db.update_place(place_id, name.strip(), description.strip())
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


@app.post("/admin/places/{place_id}/delete")
async def delete_place(
    place_id: int,
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    db.delete_place(place_id)
    return RedirectResponse("/admin", status_code=303)


# ── Section management ────────────────────────────────────────────────────────

@app.post("/admin/places/{place_id}/sections/add")
async def add_section(
    place_id: int,
    name: Annotated[str, Form()],
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    if name.strip():
        db.create_section(place_id, name.strip())
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


@app.post("/admin/sections/{section_id}/delete")
async def delete_section(
    section_id: int,
    place_id: Annotated[int, Form()],
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    db.delete_section(section_id)
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


# ── Item management ───────────────────────────────────────────────────────────

@app.post("/admin/sections/{section_id}/items/add")
async def add_item(
    section_id: int,
    place_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    item_type: Annotated[str, Form()] = "pass_fail",
    require_photo: Annotated[str, Form()] = "",
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    if name.strip():
        db.create_item(section_id, name.strip(), item_type, bool(require_photo))
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


@app.post("/admin/items/{item_id}/delete")
async def delete_item(
    item_id: int,
    place_id: Annotated[int, Form()],
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    db.delete_item(item_id)
    return RedirectResponse(f"/admin/places/{place_id}", status_code=303)


# ── Inspections list ──────────────────────────────────────────────────────────

@app.get("/admin/inspections", response_class=HTMLResponse)
async def admin_inspections(
    request: Request,
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    inspections = db.list_inspections()
    return templates.TemplateResponse(
        "admin/inspections.html",
        {"request": request, "inspections": inspections},
    )


@app.get("/admin/inspections/{inspection_id}/pdf")
async def admin_pdf(
    inspection_id: int,
    session: Annotated[Optional[str], Cookie()] = None,
):
    if redir := _require_admin(session):
        return redir
    inspection = db.get_inspection(inspection_id)
    if not inspection or not inspection.get("pdf_path"):
        return HTMLResponse("PDF not found", status_code=404)
    pdf_path = Path(inspection["pdf_path"])
    if not pdf_path.exists():
        return HTMLResponse("PDF file missing", status_code=404)
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"inspection_{inspection_id}.pdf",
    )


# ── Telegram /register command support ───────────────────────────────────────
# Add this webhook to the existing Telegram bot in ai_bot/telegram_bot.py
# so inspectors can register by sending /register <their name> to the bot.
