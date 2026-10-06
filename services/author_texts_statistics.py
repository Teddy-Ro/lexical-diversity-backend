import re
from dataclasses import dataclass

AUTHOR_TEXTS_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[-’'][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True, slots=True)
class AuthorTextsStatistics:
    text_length: int
    unique_token_count: int
    ratio: float


def calculate_author_texts_statistics(text_content: str) -> AuthorTextsStatistics:
    tokens = [
        token.casefold() for token in AUTHOR_TEXTS_TOKEN_PATTERN.findall(text_content)
    ]
    text_length = len(tokens)
    unique_token_count = len(set(tokens))
    ratio = unique_token_count / text_length if text_length else 0.0
    return AuthorTextsStatistics(text_length, unique_token_count, ratio)
