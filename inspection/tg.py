"""Send inspection PDF via Telegram Bot API (direct HTTP, no polling)."""

from __future__ import annotations

import httpx
from pathlib import Path
from typing import Optional

from . import config


async def send_pdf(chat_id: str, pdf_path: Path, caption: str) -> bool:
    """Send a PDF file to a Telegram chat. Returns True on success."""
    if not chat_id or not config.TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(pdf_path, "rb") as f:
                resp = await client.post(
                    url,
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": (pdf_path.name, f, "application/pdf")},
                )
        return resp.status_code == 200
    except Exception as exc:
        print(f"[Telegram] Failed to send to {chat_id}: {exc}")
        return False


async def send_message(chat_id: str, text: str) -> bool:
    if not chat_id or not config.TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, data={"chat_id": chat_id, "text": text})
        return resp.status_code == 200
    except Exception as exc:
        print(f"[Telegram] sendMessage failed: {exc}")
        return False


async def notify_inspection(
    pdf_path: Path,
    inspection: dict,
    place: dict,
    drive_url: Optional[str] = None,
) -> None:
    """Send PDF to the inspector and admin."""
    caption = (
        f"📋 Inspection Report\n"
        f"Place: {place['name']}\n"
        f"Inspector: {inspection['inspector_name']}\n"
        f"Date: {inspection.get('completed_at', '')}"
    )
    if drive_url:
        caption += f"\n📁 Drive: {drive_url}"

    targets = []
    if inspection.get("inspector_telegram_id"):
        targets.append(inspection["inspector_telegram_id"])
    if config.ADMIN_TELEGRAM_CHAT_ID and config.ADMIN_TELEGRAM_CHAT_ID not in targets:
        targets.append(config.ADMIN_TELEGRAM_CHAT_ID)

    for chat_id in targets:
        await send_pdf(chat_id, pdf_path, caption)
