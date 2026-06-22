import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_CHAT_ID", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Company Name")
# Path to Google service account JSON file (or leave empty to skip Drive upload)
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
# Google Drive folder ID where inspections will be uploaded
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
APP_HOST = os.environ.get("INSPECTION_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("INSPECTION_PORT", "8080"))
