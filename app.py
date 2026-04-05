import json
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.code_agent import handle_code_query, stream_code_query
from agents.knowledge_agent import handle_knowledge_query, stream_knowledge_query
from agents.router import route_query
from memory.store import (
    add_message,
    create_session,
    delete_session,
    get_session,
    get_session_summary,
    list_sessions,
    rename_session,
)

app = FastAPI(title="AI Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionRenameRequest(BaseModel):
    title: str


def _build_chat_payload(message: str, session_id: str):
    agent_type = route_query(message)
    if agent_type == "code":
        response = handle_code_query(message, session_id)
    else:
        response = handle_knowledge_query(message, session_id)

    return {
        "agent": agent_type,
        "response": response,
        "session": get_session(session_id),
        "session_summary": get_session_summary(session_id),
    }


def _stream_chat_payload(message: str, session_id: str) -> Iterator[str]:
    agent_type = route_query(message)
    if agent_type == "code":
        chunks = stream_code_query(message, session_id)
    else:
        chunks = stream_knowledge_query(message, session_id)

    full_response = ""
    yield json.dumps(
        {
            "type": "meta",
            "agent": agent_type,
            "session": get_session_summary(session_id),
        }
    ) + "\n"

    for chunk in chunks:
        full_response += chunk
        yield json.dumps({"type": "chunk", "content": chunk}) + "\n"

    add_message(session_id, "assistant", full_response)
    yield json.dumps(
        {
            "type": "done",
            "agent": agent_type,
            "response": full_response,
            "session": get_session(session_id),
            "session_summary": get_session_summary(session_id),
        }
    ) + "\n"


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/sessions")
def get_sessions():
    return {"sessions": list_sessions()}


@app.post("/api/sessions")
def create_chat_session(req: SessionCreateRequest):
    session = create_session(req.title)
    return {"session": session, "session_summary": get_session_summary(session["id"])}


@app.get("/api/sessions/{session_id}")
def get_chat_session(session_id: str):
    session = get_session(session_id)
    return {"session": session}


@app.patch("/api/sessions/{session_id}")
def rename_chat_session(session_id: str, req: SessionRenameRequest):
    session = rename_session(session_id, req.title)
    return {"session": session, "session_summary": get_session_summary(session_id)}


@app.delete("/api/sessions/{session_id}")
def delete_chat_session(session_id: str):
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    session = create_session() if not req.session_id else get_session(req.session_id)
    return _build_chat_payload(req.message, session["id"])


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    session = create_session() if not req.session_id else get_session(req.session_id)
    return StreamingResponse(
        _stream_chat_payload(req.message, session["id"]),
        media_type="application/x-ndjson",
    )
