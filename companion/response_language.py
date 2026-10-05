from __future__ import annotations

import re
from typing import Iterable


# A bounded P0 policy, not a general language classifier.
_LANGUAGES = {
    "japanese": "Japanese", "日本語": "Japanese",
    "english": "English", "英語": "English",
    "chinese": "Chinese", "中国語": "Chinese",
    "korean": "Korean", "韓国語": "Korean",
    "french": "French", "フランス語": "French",
    "german": "German", "ドイツ語": "German",
    "spanish": "Spanish", "スペイン語": "Spanish",
}
_ALIASES = "|".join(sorted(_LANGUAGES, key=len, reverse=True))
_CODE = re.compile(r"```.*?(?:```|$)|~~~.*?(?:~~~|$)|`[^`]*(?:`|$)", re.DOTALL)
_QUOTED = re.compile(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"\n]*"')
_REQUEST = re.compile(
    rf"\b(?:answer|respond|reply|write|output)(?:\s+to\s+me)?\s+in\s+(?P<en>{_ALIASES})\b"
    rf"|(?P<ja>{_ALIASES})\s*で\s*(?:答えて|回答して|返答して|返信して|応答して|説明して|書いて|話して|お願い(?:します)?|[。.!！\s]*$)"
    rf"|(?:^|[.!?]\s+)(?P<please>{_ALIASES})\s*,?\s*please\b"
    rf"|\b(?:output|response|reply|answer)\s+language\s*:\s*(?P<setting>{_ALIASES})\b",
    re.IGNORECASE,
)
_NEGATED_PREFIX = re.compile(r"(?:\bnot|\bnever|\bavoid|don't)\s+$", re.IGNORECASE)
_NEGATED_SUFFIX = re.compile(r"\s*(?:は)?(?:ほしく|欲しく)?(?:ない|なく)")
_ASCII_TOKEN = re.compile(r"[A-Za-z0-9_]+(?:[./:\-][A-Za-z0-9_]+)*")
_IDENTIFIER_MARKERS = re.compile(r"[0-9_./:\-]")
_JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")


def _language(text: str) -> str | None:
    prose = _CODE.sub(" ", text)
    requests = _QUOTED.sub(" ", prose)
    explicit = None
    for match in _REQUEST.finditer(requests):
        if _NEGATED_PREFIX.search(requests[:match.start()]) or _NEGATED_SUFFIX.match(requests[match.end():]):
            continue
        alias = next(value for value in match.groupdict().values() if value is not None)
        explicit = _LANGUAGES[alias.casefold()]
    if explicit:
        return explicit

    # Code, URLs, and versioned identifiers must not outweigh Japanese prose.
    if _JAPANESE.search(requests) or _LATIN.search(requests):
        prose = requests
    prose = re.sub(r"https?://\S+", " ", prose)
    prose = _ASCII_TOKEN.sub(lambda match: " " if _IDENTIFIER_MARKERS.search(match[0]) else match[0], prose)
    japanese = len(_JAPANESE.findall(prose))
    latin = len(_LATIN.findall(prose))
    if japanese:
        if len(_ASCII_TOKEN.findall(prose)) <= 2:
            return "Japanese"  # Short Japanese questions such as "Pythonは？".
        # Japanese conveys more per character; English prose with a short Japanese
        # term still stays English. This weight is a small deterministic heuristic.
        return "Japanese" if japanese * 2 >= latin else "English"
    return "English" if latin else None


def response_language_policy(canonical_user_text: str, recent_user_texts: Iterable[str] = ()) -> str:
    language = _language(canonical_user_text)
    if language is None:
        # Language-neutral input (e.g. a model ID) retains the latest user's language.
        language = next((found for text in reversed(tuple(recent_user_texts)) if (found := _language(text))), "English")
    switch = "another language" if language == "English" else "English"
    return (
        f"Output language: {language}.\n"
        f"Respond naturally in {language}.\n"
        f"Do not switch to {switch} unless the user explicitly asks for {switch}, "
        f"or {switch} is necessary for quoted text, code, identifiers, or technical terms.\n"
        "The language of history, Memory, Identity, and internal instructions does not override this output language."
    )
