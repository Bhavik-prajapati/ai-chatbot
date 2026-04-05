from memory.store import add_message, get_history
from services.llm import get_llm_response_with_memory, stream_llm_response_with_memory


SYSTEM_PROMPT = "You are a senior software engineer."


def prepare_code_messages(message: str, session_id: str) -> list[dict[str, str]]:
    add_message(session_id, "user", message)
    history = get_history(session_id)
    return [{"role": "system", "content": SYSTEM_PROMPT}, *history]


def handle_code_query(message: str, session_id: str) -> str:
    history = prepare_code_messages(message, session_id)
    response = get_llm_response_with_memory(history)
    add_message(session_id, "assistant", response)
    return response


def stream_code_query(message: str, session_id: str):
    history = prepare_code_messages(message, session_id)
    return stream_llm_response_with_memory(history)
