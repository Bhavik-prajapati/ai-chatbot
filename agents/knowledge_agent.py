from agents.search_agent import search_web
from memory.store import add_message, get_history
from services.llm import get_llm_response_with_memory, stream_llm_response_with_memory


SYSTEM_PROMPT = """
You are Nova, a helpful AI assistant.
When the conversation includes fresh web search results, treat them as the primary source for current facts.
If the user asks about recent or time-sensitive events, do not claim your knowledge is outdated when live search context is provided.
If the search results are insufficient, say that clearly instead of inventing details.
""".strip()


def needs_search(message: str) -> bool:
    keywords = [
        "current",
        "latest",
        "today",
        "yesterday",
        "tomorrow",
        "now",
        "recent",
        "news",
        "weather",
        "score",
        "result",
        "match",
        "live",
        "vs",
        "fixture",
        "ipl",
        "won",
    ]
    return any(word in message.lower() for word in keywords)


def prepare_knowledge_messages(message: str, session_id: str) -> list[dict[str, str]]:
    add_message(session_id, "user", message)
    history = get_history(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]

    if needs_search(message):
        search_results = search_web(message)
        messages.append(
            {
                "role": "system",
                "content": f"Use this real-time data when it helps:\n{search_results}",
            }
        )

    return messages


def handle_knowledge_query(message: str, session_id: str) -> str:
    history = prepare_knowledge_messages(message, session_id)
    response = get_llm_response_with_memory(history)
    add_message(session_id, "assistant", response)
    return response


def stream_knowledge_query(message: str, session_id: str):
    history = prepare_knowledge_messages(message, session_id)
    return stream_llm_response_with_memory(history)
