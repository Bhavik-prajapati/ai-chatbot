import os
from typing import Iterator

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL_NAME = "llama-3.1-8b-instant"
_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def get_llm_response(message: str) -> str:
    try:
        response = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": message},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        return f"Error: {exc}"


def get_llm_response_with_memory(messages: list[dict[str, str]]) -> str:
    try:
        response = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        return f"Error: {exc}"


def stream_llm_response_with_memory(messages: list[dict[str, str]]) -> Iterator[str]:
    try:
        stream = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
    except Exception as exc:
        yield f"Error: {exc}"
