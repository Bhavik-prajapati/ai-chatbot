def route_query(message:str):
    message_lower=message.lower()
    if any(word in message_lower for word in ["code", "python", "javascript", "bug", "error", "api"]):
        return "code"
    
    return "knowledge"

