import secrets
import string

def generate_event_code():
    characters = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(characters) for _ in range(6))
    return f"HF-{code}"

def generate_coordinator_token():
    return secrets.token_urlsafe(32)

def generate_anonymous_id():
    return "V-" + secrets.token_hex(4).upper()
