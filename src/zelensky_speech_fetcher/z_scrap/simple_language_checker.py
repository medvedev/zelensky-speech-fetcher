import string

allowed_chars = set(string.ascii_letters + string.digits + string.punctuation + " ")

max_allowed_percentage = 0.035

def looks_like_english_text(text: str) -> bool:
    if not text:
        return True
    invalid_count = sum(1 for char in text if char not in allowed_chars)
    return invalid_count / len(text) < max_allowed_percentage
