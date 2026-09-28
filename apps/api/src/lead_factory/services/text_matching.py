from __future__ import annotations

import re


def contains_term(text: str, term: str) -> bool:
    words = [re.escape(part) for part in term.casefold().split()]
    if not words:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)"
    return re.search(pattern, text.casefold(), flags=re.UNICODE) is not None
