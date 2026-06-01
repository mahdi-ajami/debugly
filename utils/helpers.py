import uuid


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


def truncate(text: str, max_len: int = 200) -> str:
    return text if len(text) <= max_len else text[:max_len] + "..."
