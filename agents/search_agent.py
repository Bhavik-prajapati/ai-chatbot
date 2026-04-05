from ddgs import DDGS

def search_web(query: str):
    results = []

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=3):
            results.append(r["body"])

    return "\n".join(results)