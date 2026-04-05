from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


chat_sessions: "OrderedDict[str, dict[str, Any]]" = OrderedDict()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trim_title(text: str, max_length: int = 48) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "New chat"
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1].rstrip()}..."


def _ensure_session(session_id: str | None) -> dict[str, Any]:
    if session_id and session_id in chat_sessions:
        session = chat_sessions[session_id]
        session["updated_at"] = _now_iso()
        chat_sessions.move_to_end(session_id)
        return session

    new_session_id = session_id or str(uuid4())
    session = {
        "id": new_session_id,
        "title": "New chat",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": [],
    }
    chat_sessions[new_session_id] = session
    return session


def create_session(title: str | None = None) -> dict[str, Any]:
    session = _ensure_session(None)
    if title:
        session["title"] = _trim_title(title)
    return get_session(session["id"])


def list_sessions() -> list[dict[str, Any]]:
    sessions = list(chat_sessions.values())
    sessions.reverse()
    return [get_session_summary(session["id"]) for session in sessions]


def get_session(session_id: str) -> dict[str, Any]:
    session = _ensure_session(session_id)
    return {
        "id": session["id"],
        "title": session["title"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "messages": [message.copy() for message in session["messages"]],
    }


def get_session_summary(session_id: str) -> dict[str, Any]:
    session = _ensure_session(session_id)
    messages = session["messages"]
    preview = messages[-1]["content"] if messages else ""
    return {
        "id": session["id"],
        "title": session["title"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "message_count": len(messages),
        "preview": _trim_title(preview, 80),
    }


def delete_session(session_id: str) -> bool:
    return chat_sessions.pop(session_id, None) is not None


def rename_session(session_id: str, title: str) -> dict[str, Any]:
    session = _ensure_session(session_id)
    session["title"] = _trim_title(title)
    session["updated_at"] = _now_iso()
    return get_session(session_id)


def add_message(session_id: str, role: str, content: str) -> dict[str, Any]:
    session = _ensure_session(session_id)
    message = {
        "role": role,
        "content": content,
        "created_at": _now_iso(),
    }
    session["messages"].append(message)
    session["updated_at"] = _now_iso()

    if role == "user" and len(session["messages"]) == 1:
        session["title"] = _trim_title(content)

    return message.copy()


def get_history(session_id: str) -> list[dict[str, str]]:
    session = _ensure_session(session_id)
    return [
        {"role": message["role"], "content": message["content"]}
        for message in session["messages"]
    ]
