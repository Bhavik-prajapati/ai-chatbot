from ddgs import DDGS


def search_web(query: str) -> str:
    results: list[str] = []

    with DDGS() as ddgs:
        for result in ddgs.text(query, max_results=5):
            title = result.get("title", "").strip()
            body = result.get("body", "").strip()
            href = result.get("href", "").strip()

            parts = [part for part in [title, body, href] if part]
            if parts:
                results.append(" | ".join(parts))

    return "\n".join(results)
