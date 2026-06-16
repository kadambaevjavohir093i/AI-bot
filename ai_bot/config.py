import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]

PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")

VOICE_APP_HOST = os.environ.get("VOICE_APP_HOST", "0.0.0.0")
VOICE_APP_PORT = int(os.environ.get("VOICE_APP_PORT", "8000"))
