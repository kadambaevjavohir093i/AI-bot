"""Generates the assistant's side of a phone conversation with Claude."""

from anthropic import Anthropic

from . import config

_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

END_MARKER = "[END_CALL]"

SYSTEM_PROMPT_TEMPLATE = """\
You are a voice assistant placing a real phone call on behalf of your user.
Speak naturally, the way a person would on the phone: short sentences, no
markdown, no lists, no emoji.

Your task for this call, as described by your user: {instructions}

Rules:
- Stay in character as someone calling for that purpose. If asked who you
  are, say you're an assistant calling on behalf of your user (you may say
  the user's name if it's given in the task) because they're busy right now.
- Keep each turn brief (1-3 sentences), like real spoken dialogue.
- Once the purpose of the call is accomplished (or the other person clearly
  wants to end the call), say a short goodbye and then output the exact
  token {end_marker} on its own at the very end of your reply.
- Never output {end_marker} before you have actually said a goodbye out loud
  in the same reply.
"""


def opening_line(instructions: str) -> str:
    return _generate(instructions, history=[])


def next_line(instructions: str, history: list[dict]) -> str:
    return _generate(instructions, history=history)


def _generate(instructions: str, history: list[dict]) -> str:
    system = SYSTEM_PROMPT_TEMPLATE.format(instructions=instructions, end_marker=END_MARKER)
    messages = history or [{"role": "user", "content": "(The call has just connected. Greet them and start.)"}]
    response = _client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=200,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
