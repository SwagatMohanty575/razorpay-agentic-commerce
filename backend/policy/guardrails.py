import re

BLOCKED_PATTERNS = [
    (r'\b(select|insert|update|delete|drop|alter|union)\b[\s\S]{0,40}\b(from|into|table|where|database)\b',
     "This looks like a database query rather than a shopping request."),
    (r'--\s|\bor\s+1\s*=\s*1\b|;\s*drop\b',
     "This looks like an attempt to inject database commands."),
    (r'\b(ignore|disregard|forget|override)\b[\s\S]{0,40}\b(previous|prior|above|earlier|your)\b[\s\S]{0,25}\b(instruction|prompt|rule|guideline)',
     "Instructions to the shopping agent can't be overridden through the search box."),
    (r'\b(system prompt|your instructions|reveal your|show your prompt|print your prompt|you are now)\b',
     "The agent's configuration isn't available through the storefront."),
    (r'```|\bdef\s+\w+\s*\(|\bimport\s+\w+|\bfunction\s+\w+\s*\(|<script|\bconsole\.log\b',
     "This looks like code rather than a product request."),
    (r'\b(api[_\s-]?key|secret key|password|credential|\.env|access token)\b',
     "Account and credential details aren't handled through product search."),
    (r'\bset\s+(the\s+)?price\s+to\b|\bmake\s+it\s+free\b|\b100%\s*(off|discount)\b|\bgive\s+me\s+.{0,20}for\s+free\b',
     "Prices come from the merchant's catalogue and can't be set from a search request."),
    (r'\b(write|generate|compose)\s+(me\s+)?(a|an)\s+(poem|story|essay|song|joke|email|blog|article)\b',
     "This store's agent only handles product requests."),
    (r'\b(translate this|summarise this|summarize this|debug my|fix my code|explain how to code)\b',
     "This store's agent only handles product requests."),
]

MAX_QUERY_CHARS = 400


def check_query(raw_query: str) -> tuple[bool, str | None]:
    """Deterministic input gate — runs before the query reaches the LLM.
    Returns (allowed, reason_if_blocked)."""
    if not raw_query or not raw_query.strip():
        return False, "Tell us what you're shopping for."

    if len(raw_query) > MAX_QUERY_CHARS:
        return False, f"Requests are limited to {MAX_QUERY_CHARS} characters. Try describing the product more briefly."

    lowered = raw_query.lower()
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return False, reason

    return True, None