"""Generate a PDF inspection report using reportlab."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .db import PDF_DIR, UPLOAD_DIR

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm

GREEN = colors.HexColor("#27ae60")
RED = colors.HexColor("#e74c3c")
ORANGE = colors.HexColor("#e67e22")
GREY_LIGHT = colors.HexColor("#f5f5f5")
GREY_MID = colors.HexColor("#cccccc")
BLUE_DARK = colors.HexColor("#1a3a5c")

styles = getSampleStyleSheet()

_h1 = ParagraphStyle("h1", parent=styles["Normal"], fontSize=18, fontName="Helvetica-Bold", textColor=BLUE_DARK, spaceAfter=4)
_h2 = ParagraphStyle("h2", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold", textColor=colors.white)
_body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=12)
_small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#555555"))
_result_pass = ParagraphStyle("rpass", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=GREEN)
_result_fail = ParagraphStyle("rfail", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=RED)
_result_na = ParagraphStyle("rna", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=ORANGE)


def _result_para(result: str) -> Paragraph:
    r = (result or "").strip().upper()
    if r in ("PASS", "YES"):
        return Paragraph(f"✓ {r}", _result_pass)
    if r in ("FAIL", "NO"):
        return Paragraph(f"✗ {r}", _result_fail)
    return Paragraph(r or "—", _result_na)


def _maybe_image(photo_filename: str, max_w: float = 5 * cm, max_h: float = 5 * cm) -> Optional[Image]:
    if not photo_filename:
        return None
    path = UPLOAD_DIR / photo_filename
    if not path.exists():
        return None
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as pil_img:
            pil_img.thumbnail((600, 600))
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=75)
            buf.seek(0)
        img = Image(buf, width=max_w, height=max_h, kind="bound")
        return img
    except Exception:
        return None


def generate_pdf(
    inspection: Dict,
    place: Dict,
    results: List[Dict],
    company_name: str,
) -> Path:
    pdf_path = PDF_DIR / f"inspection_{inspection['id']}.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    content_width = PAGE_W - 2 * MARGIN
    story: list = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph(company_name, _h1))
    story.append(Paragraph(f"Place Inspection – {place['name']}", _body))
    story.append(Spacer(1, 0.3 * cm))

    started = inspection.get("started_at", "")
    completed = inspection.get("completed_at", "")

    def _fmt(dt_str: str) -> str:
        if not dt_str:
            return "—"
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%m/%d/%Y, %I:%M:%S %p")
        except Exception:
            return dt_str

    meta_data = [
        ["Date:", _fmt(started)],
        ["Completed:", _fmt(completed)],
        ["Inspector:", inspection.get("inspector_name", "")],
        ["Place:", place["name"]],
    ]
    meta_table = Table(meta_data, colWidths=[3 * cm, content_width - 3 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(HRFlowable(width=content_width, color=GREY_MID, thickness=1))
    story.append(Spacer(1, 0.4 * cm))

    # ── Results table ────────────────────────────────────────────────────────
    story.append(Paragraph("Inspection Report", _h1))
    story.append(Spacer(1, 0.2 * cm))

    col_item = content_width * 0.40
    col_result = content_width * 0.18
    col_detail = content_width * 0.42

    table_data: list = [
        [
            Paragraph("<b>Item</b>", _body),
            Paragraph("<b>Result</b>", _body),
            Paragraph("<b>Detail / Evidence</b>", _body),
        ]
    ]
    table_styles: list = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, GREY_MID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    # Group results by section
    sections: Dict[str, List[Dict]] = {}
    section_order: List[str] = []
    for r in results:
        sec = r["section_name"]
        if sec not in sections:
            sections[sec] = []
            section_order.append(sec)
        sections[sec].append(r)

    row_idx = 1  # 0 is header
    for sec_name in section_order:
        # Section header row
        table_data.append(
            [
                Paragraph(f"<b>{sec_name}</b>", ParagraphStyle("sh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold", textColor=colors.white)),
                "",
                "",
            ]
        )
        table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), BLUE_DARK))
        table_styles.append(("SPAN", (0, row_idx), (-1, row_idx)))
        row_idx += 1

        for res in sections[sec_name]:
            img = _maybe_image(res.get("photo_filename", ""))
            detail_content: list = []
            if res.get("detail"):
                detail_content.append(Paragraph(res["detail"], _small))
            if img:
                detail_content.append(Spacer(1, 0.2 * cm))
                detail_content.append(img)

            table_data.append(
                [
                    Paragraph(res["item_name"], _body),
                    _result_para(res.get("result", "")),
                    detail_content or Paragraph("", _body),
                ]
            )
            row_idx += 1

    results_table = Table(
        table_data,
        colWidths=[col_item, col_result, col_detail],
        repeatRows=1,
    )
    results_table.setStyle(TableStyle(table_styles))
    story.append(results_table)

    # ── Notes ────────────────────────────────────────────────────────────────
    if inspection.get("notes"):
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("<b>Notes</b>", _body))
        story.append(Paragraph(inspection["notes"], _small))

    # ── Signatures ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    sig_data = [
        [
            Paragraph("Inspector Signature:", _small),
            Paragraph("Date:", _small),
        ],
        ["_" * 35, "_" * 20],
    ]
    sig_table = Table(sig_data, colWidths=[content_width * 0.65, content_width * 0.35])
    story.append(sig_table)

    doc.build(story)
    return pdf_path
