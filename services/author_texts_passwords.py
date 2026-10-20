"""PBKDF2 password storage and constant-time digest comparison."""

import hashlib
import secrets


def hash_author_texts_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_author_texts_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, rounds, salt, expected = password_hash.split("$")
        iterations = int(rounds)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations)
        return secrets.compare_digest(digest.hex(), expected)
    except (ValueError, UnicodeError):
        return False
