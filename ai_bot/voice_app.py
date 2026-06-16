"""FastAPI app that handles Twilio's voice webhooks and drives the
turn-by-turn conversation: Twilio speech-to-text -> Claude -> Twilio
text-to-speech."""

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from . import call_manager, config, llm

app = FastAPI()


def _say_and_gather(vr: VoiceResponse, text: str) -> None:
    gather = Gather(input="speech", action="/voice/respond", method="POST", speech_timeout="auto")
    gather.say(text)
    vr.append(gather)
    # If the caller hangs up without speaking, end the call gracefully.
    vr.say("Goodbye.")
    vr.hangup()


@app.post("/voice/answer")
async def voice_answer(CallSid: str = Form(...)):
    task = call_manager.get(CallSid)
    vr = VoiceResponse()
    if task is None:
        vr.say("Sorry, something went wrong setting up this call. Goodbye.")
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    opening = llm.opening_line(task.instructions)
    opening_clean = opening.replace(llm.END_MARKER, "").strip()
    task.history.append({"role": "assistant", "content": opening})
    _say_and_gather(vr, opening_clean)
    return Response(content=str(vr), media_type="application/xml")


@app.post("/voice/respond")
async def voice_respond(
    CallSid: str = Form(...),
    SpeechResult: str = Form(""),
):
    task = call_manager.get(CallSid)
    vr = VoiceResponse()
    if task is None or task.ended:
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    task.history.append({"role": "user", "content": SpeechResult or "(no speech detected)"})
    reply = llm.next_line(task.instructions, task.history)
    task.history.append({"role": "assistant", "content": reply})

    if llm.END_MARKER in reply:
        task.ended = True
        vr.say(reply.replace(llm.END_MARKER, "").strip())
        vr.hangup()
    else:
        _say_and_gather(vr, reply)

    return Response(content=str(vr), media_type="application/xml")


@app.post("/voice/status")
async def voice_status(CallSid: str = Form(...), CallStatus: str = Form(...)):
    task = call_manager.get(CallSid)
    if task and CallStatus in ("completed", "busy", "failed", "no-answer", "canceled"):
        summary = _summarize(task)
        await _notify_telegram(task.telegram_chat_id, CallSid, CallStatus, summary)
        call_manager.discard(CallSid)
    return Response(status_code=204)


def _summarize(task: call_manager.CallTask) -> str:
    lines = []
    for turn in task.history:
        text = turn["content"].replace(llm.END_MARKER, "").strip()
        if not text:
            continue
        speaker = "Assistant" if turn["role"] == "assistant" else "Them"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines) if lines else "(no conversation captured)"


async def _notify_telegram(chat_id: int, call_sid: str, status: str, summary: str) -> None:
    text = f"Call finished ({status}).\n\n{summary}"
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})
