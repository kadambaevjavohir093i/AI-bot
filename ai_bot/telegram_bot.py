"""Telegram bot: /call <phone_number> <description> places an AI-driven
phone call via Twilio."""

import re

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from twilio.rest import Client as TwilioClient

from . import call_manager, config

PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")  # loose E.164-ish check

_twilio = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send /call <phone_number> <what I should say/do>\n"
        "Example: /call +15551234567 Wish Jake a happy birthday on my behalf, "
        "say I'm busy with work today."
    )


async def call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /call <phone_number> <description>")
        return

    phone_number = context.args[0]
    instructions = " ".join(context.args[1:])

    if not PHONE_RE.match(phone_number):
        await update.message.reply_text(
            "That doesn't look like a valid phone number. Use international "
            "format, e.g. +15551234567."
        )
        return

    task = call_manager.CallTask(
        phone_number=phone_number,
        instructions=instructions,
        telegram_chat_id=update.effective_chat.id,
    )

    twilio_call = _twilio.calls.create(
        to=phone_number,
        from_=config.TWILIO_PHONE_NUMBER,
        url=f"{config.PUBLIC_BASE_URL}/voice/answer",
        status_callback=f"{config.PUBLIC_BASE_URL}/voice/status",
        status_callback_event=["completed", "busy", "failed", "no-answer", "canceled"],
    )
    call_manager.register(twilio_call.sid, task)

    await update.message.reply_text(f"Calling {phone_number} now. I'll let you know how it goes.")


def build_application() -> Application:
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("call", call))
    return application
