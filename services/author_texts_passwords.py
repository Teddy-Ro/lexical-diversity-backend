"""Password storage for the user model; authentication is a later lab."""

import hashlib
import secrets


def hash_author_texts_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"
