# AI calling assistant (Telegram bot)

Send the bot a phone number and a description of what you want done, and it
places a real phone call (via Twilio) where Claude carries the conversation
on your behalf.

Example:

```
/call +15551234567 Wish Jake a happy birthday on my behalf, say I'm busy with work today.
```

## How it works

- `ai_bot/telegram_bot.py` — Telegram `/call` command, places the outbound
  call through Twilio's REST API and registers the task.
- `ai_bot/voice_app.py` — FastAPI app exposing the Twilio webhooks:
  - `/voice/answer` — called when the callee picks up; Claude generates the
    opening line, Twilio speaks it (TTS) and listens for a reply (STT).
  - `/voice/respond` — called with the transcribed speech each turn; feeds
    the conversation history to Claude and returns the next line, looping
    until Claude signals the call is done.
  - `/voice/status` — called when the call ends; sends a summary back to
    the Telegram chat that requested it.
- `ai_bot/llm.py` — wraps the Anthropic API, instructing Claude to act as a
  voice assistant calling on the user's behalf, in character, until the
  task is complete.
- `ai_bot/call_manager.py` — in-memory map of Twilio `CallSid` -> task state
  (phone number, instructions, conversation history). Single-process only;
  swap for Redis if you need multiple workers.

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `ANTHROPIC_API_KEY` — Anthropic API key
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` — from
     the Twilio console; the number must have Voice capability
   - `PUBLIC_BASE_URL` — a public HTTPS URL that reaches this process on
     `VOICE_APP_PORT` (e.g. an `ngrok http 8000` tunnel while developing,
     or your real domain once deployed)
3. Run: `python -m ai_bot.main`

## Notes / limitations

- Speech recognition and TTS use Twilio's built-in engines (`<Gather
  input="speech">` / `<Say>`), not a low-latency realtime voice model, so
  there's a short pause each turn — fine for short calls like this, but
  not as snappy as a full duplex voice stream.
- This is a v1 scaffold: no persistence across restarts, no auth on who can
  use the Telegram bot (anyone who messages it can place calls — consider
  restricting `telegram_chat_id` to your own before exposing it publicly),
  and no outbound-call rate limiting.
