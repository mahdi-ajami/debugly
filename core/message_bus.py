import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    type: str = "request"
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    in_reply_to: str = ""

    def reply(self, payload: dict) -> "AgentMessage":
        return AgentMessage(
            sender=self.receiver,
            receiver=self.sender,
            type="response",
            payload=payload,
            in_reply_to=self.id,
        )


class MessageBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[AgentMessage] = []
        self._max_history = 1000

    def send(self, msg: AgentMessage):
        self._history.append(msg)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        for handler in self._handlers.get(msg.receiver, []):
            handler(msg)
        for handler in self._handlers.get("*", []):
            handler(msg)

    def subscribe(self, agent_name: str, handler: Callable):
        self._handlers[agent_name].append(handler)

    def unsubscribe(self, agent_name: str, handler: Callable):
        self._handlers[agent_name] = [h for h in self._handlers[agent_name] if h != handler]

    def broadcast(self, msg: AgentMessage):
        msg.receiver = "*"
        self.send(msg)

    def request(self, receiver: str, payload: dict, sender: str = "") -> AgentMessage:
        msg = AgentMessage(sender=sender or "system", receiver=receiver, type="request", payload=payload)
        self.send(msg)
        return msg

    def respond(self, original: AgentMessage, payload: dict):
        reply = original.reply(payload)
        self.send(reply)
        return reply

    def get_history(self, agent_name: str | None = None, limit: int = 50) -> list[AgentMessage]:
        if agent_name:
            return [m for m in self._history[-limit:] if m.sender == agent_name or m.receiver == agent_name]
        return self._history[-limit:]

    def clear(self):
        self._history.clear()
        self._handlers.clear()

    def waiting_for(self, receiver: str, since: str = "") -> list[AgentMessage]:
        result = []
        for m in reversed(self._history):
            if m.receiver == receiver and m.type == "request":
                if since and m.timestamp < since:
                    break
                result.append(m)
        return result
