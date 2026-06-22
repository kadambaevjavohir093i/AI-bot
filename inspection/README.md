# Inspection Web App

A mobile-friendly web app for photo-based place inspections. Inspectors pick a
place, fill out a checklist (with photos), and submit. The app generates a PDF
report, saves it to Google Drive (optional), and sends it via Telegram to both
the inspector and the admin. Only admins can add places and edit checklists.

## Quick start (local testing)

From the project root (`AI-bot/`):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) load the example truck checklist from the sample PDF
python -m inspection.seed

# 3. Set the minimum environment variables
export TELEGRAM_BOT_TOKEN="123456:your-bot-token"
export ADMIN_TELEGRAM_CHAT_ID="your-numeric-chat-id"   # message @userinfobot
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="pick-a-strong-password"

# 4. Run it
python run_inspection.py
```

Then open:

- **Inspectors:** http://localhost:8080/
- **Admin panel:** http://localhost:8080/admin/login

To test from your phone on the same Wi-Fi, find your computer's local IP
(e.g. `192.168.1.20`) and visit `http://192.168.1.20:8080/` on the phone.

> You can put the same variables in a `.env` file in the project root instead of
> exporting them — they're loaded automatically.

## How it works

1. **Admin** logs in at `/admin`, adds a **Place**, then builds its checklist:
   **Sections** (e.g. INTERIOR, EXTERIOR) each containing **Items**. Each item is
   PASS/FAIL, YES/NO, or free text, and can be marked "photo required".
2. **Inspector** opens `/`, taps a place, enters their name + Telegram chat ID,
   fills the checklist (taking photos), and submits.
3. The app:
   - generates a PDF report,
   - uploads it to Google Drive (if configured),
   - sends the PDF over Telegram to the inspector and the admin.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes (for Telegram) | Bot token from @BotFather |
| `ADMIN_TELEGRAM_CHAT_ID` | yes (for Telegram) | Admin chat ID; always gets every PDF |
| `ADMIN_USERNAME` | recommended | Admin login (default `admin`) |
| `ADMIN_PASSWORD` | recommended | Admin login (default `changeme123` — change it) |
| `COMPANY_NAME` | optional | Shown in the PDF header |
| `SECRET_KEY` | optional | Session secret |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | optional | Path to a Google service-account JSON key |
| `GOOGLE_DRIVE_FOLDER_ID` | optional | Drive folder ID to upload PDFs into |
| `INSPECTION_HOST` / `INSPECTION_PORT` | optional | Defaults `0.0.0.0` / `8080` |

If the Google variables are unset, Drive upload is skipped silently and
everything else still works.

## Getting your Telegram chat ID

Message **@userinfobot** on Telegram — it replies with your numeric ID. Each
inspector enters their own ID on the inspection form so they receive their copy
of the PDF.

## Google Drive setup (optional)

1. In Google Cloud Console, create a **service account** and download its JSON key.
2. Enable the **Google Drive API** for that project.
3. Create a Drive folder, then **share** it with the service account's email
   (`...@...iam.gserviceaccount.com`) as Editor.
4. Set `GOOGLE_SERVICE_ACCOUNT_FILE` to the JSON path and `GOOGLE_DRIVE_FOLDER_ID`
   to the folder ID (the part of the folder URL after `/folders/`).
