from agents.search_agent import search_web
from memory.store import add_message, get_history
from services.llm import get_llm_response_with_memory, stream_llm_response_with_memory


def needs_search(message: str) -> bool:
    keywords = ["current", "latest", "today", "weather", "news"]
    return any(word in message.lower() for word in keywords)


def prepare_knowledge_messages(message: str, session_id: str) -> list[dict[str, str]]:
    add_message(session_id, "user", message)
    history = get_history(session_id)

    if needs_search(message):
        search_results = search_web(message)
        history.append(
            {
                "role": "system",
                "content": f"Use this real-time data when it helps:\n{search_results}",
            }
        )

    return history


def handle_knowledge_query(message: str, session_id: str) -> str:
    history = prepare_knowledge_messages(message, session_id)
    response = get_llm_response_with_memory(history)
    add_message(session_id, "assistant", response)
    return response


def stream_knowledge_query(message: str, session_id: str):
    history = prepare_knowledge_messages(message, session_id)
    return stream_llm_response_with_memory(history)
