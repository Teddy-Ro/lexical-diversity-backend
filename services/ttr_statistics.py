import re
from dataclasses import dataclass

TTR_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[-’'][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True, slots=True)
class TTRStatistics:
    text_length: int
    unique_token_count: int
    ratio: float


def calculate_ttr_statistics(text_content: str) -> TTRStatistics:
    tokens = [token.casefold() for token in TTR_TOKEN_PATTERN.findall(text_content)]
    text_length = len(tokens)
    unique_token_count = len(set(tokens))
    ratio = unique_token_count / text_length if text_length else 0.0
    return TTRStatistics(text_length, unique_token_count, ratio)
