"""In-memory registry of active calls and their conversation state.

A real deployment with multiple workers would need shared storage (e.g.
Redis) instead of a process-local dict, but for a single-process bot this
is sufficient.
"""

from dataclasses import dataclass, field


@dataclass
class CallTask:
    phone_number: str
    instructions: str
    telegram_chat_id: int
    history: list[dict] = field(default_factory=list)
    ended: bool = False


_calls: dict[str, CallTask] = {}


def register(call_sid: str, task: CallTask) -> None:
    _calls[call_sid] = task


def get(call_sid: str) -> CallTask | None:
    return _calls.get(call_sid)


def discard(call_sid: str) -> None:
    _calls.pop(call_sid, None)
