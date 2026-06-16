"""Entry point: runs the Telegram bot (polling) and the Twilio voice
webhook server (FastAPI/uvicorn) together in one process."""

import asyncio

import uvicorn

from . import config
from .telegram_bot import build_application
from .voice_app import app as voice_app


async def main() -> None:
    telegram_app = build_application()

    uvicorn_config = uvicorn.Config(
        voice_app, host=config.VOICE_APP_HOST, port=config.VOICE_APP_PORT, log_level="info"
    )
    server = uvicorn.Server(uvicorn_config)

    async with telegram_app:
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        try:
            await server.serve()
        finally:
            await telegram_app.updater.stop()
            await telegram_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
