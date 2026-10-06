"""Lab 3 singleton; replace this dependency with a Redis session in lab 4."""

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AuthorTextsCurrentUser:
    author_texts_user_id: int


@lru_cache(maxsize=1)
def get_current_author_texts_user() -> AuthorTextsCurrentUser:
    return AuthorTextsCurrentUser(author_texts_user_id=1)
