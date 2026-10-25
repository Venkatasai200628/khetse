"""Voice listing-draft parser: free-form transcript → structured fields.

Pure functions only — no database, no settings, no network — so every rule is
deterministic and unit-testable. The caller supplies the commodity catalogue
rows to match against.

Design rule: **never guess.** A field is extracted only on an explicit
textual signal (a number glued to a unit word, an amount next to a currency
marker, a named relative day, a commodity name/synonym). Anything else stays
``None`` and the endpoint reports it in ``fields_needing_confirmation``.

Understood signals
------------------
- quantity: Latin AND Indic digits, optionally decimal, followed by a unit
  word — English ``kg/kgs/quintal(s)/ton(ne)(s)/dozen`` and Telugu
  ``కేజీలు/కిలోలు (kg), క్వింటాల్ (quintal), టన్ను (tonne), డజను (dozen)``,
  including the mixed-script plural ``kgల``.
- price: an amount adjacent to ``₹ / rupees / Rs / INR / రూ / రూపాయలు`` or
  followed by ``per <unit>`` → integer paise (₹20 → 2000).
- availability: ``today/tomorrow/day after (tomorrow)`` and
  ``ఈరోజు (today) / రేపు (tomorrow) / ఎల్లుడు (day after)`` → ISO date.
  (In availability talk ``ఎల్లుడు`` is treated as the day after, per spec.)
- commodity: case-insensitive substring match of the transcript against
  ``name_en / name_te / name_hi`` of the supplied catalogue rows, plus a
  small transliteration/synonym map (``tamata``/``tomato``/``టమాటా``,
  ``ulli``/``onion``/``ఉల్లి``, …).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Iterable

# --- Digit normalisation (Indic → Latin) ------------------------------------

# Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada,
# Malayalam digit blocks — all map to ASCII 0-9.
_INDIC_DIGIT_BASES = (
    0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66,
)
_DIGIT_TRANSLATION = {
    ord(chr(base + offset)): str(offset)
    for base in _INDIC_DIGIT_BASES
    for offset in range(10)
}

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

_TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def normalize_digits(text: str) -> str:
    """Convert Indic numerals (౫, ५, …) to Latin digits."""
    return text.translate(_DIGIT_TRANSLATION)


def detect_language(text: str, fallback: str = "en") -> str:
    """Script-based language detection with a caller-supplied fallback."""
    if _TELUGU_RE.search(text):
        return "te"
    if _DEVANAGARI_RE.search(text):
        return "hi"
    return fallback


# --- Quantity + unit ---------------------------------------------------------

# Spoken unit word → canonical UnitEnum value.
UNIT_TOKENS: dict[str, str] = {
    # English (incl. the mixed-script Telugu plural "kg" + ల)
    "kg": "kg",
    "kgs": "kg",
    "kgల": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "quintal": "quintal",
    "quintals": "quintal",
    "tonne": "tonne",
    "tonnes": "tonne",
    "ton": "tonne",
    "tons": "tonne",
    "dozen": "dozen",
    "dozens": "dozen",
    # Telugu
    "కేజీలు": "kg",
    "కిలోలు": "kg",
    "కేజీ": "kg",
    "కిలో": "kg",
    "క్వింటాల్": "quintal",
    "టన్ను": "tonne",
    "డజను": "dozen",
}

# Longest-first alternation so "quintals" wins over "quintal", "kgల" over "kg".
_UNIT_AFTER_NUMBER_RE = re.compile(
    r"\s*(" + "|".join(re.escape(t) for t in sorted(UNIT_TOKENS, key=len, reverse=True)) + ")",
    re.IGNORECASE,
)


def extract_quantity(text: str) -> tuple[float | None, str | None, tuple[int, int] | None]:
    """First ``<number> <unit word>`` occurrence.

    Returns ``(quantity, unit, span_of_number)`` or ``(None, None, None)``.
    A bare number without a unit word is never taken as a quantity.
    """
    for match in _NUMBER_RE.finditer(text):
        unit_match = _UNIT_AFTER_NUMBER_RE.match(text, match.end())
        if unit_match:
            unit = UNIT_TOKENS[unit_match.group(1).lower()]
            return float(match.group()), unit, match.span()
    return None, None, None


# --- Price -------------------------------------------------------------------

# Markers that may sit right before the amount: "₹2000", "రూ 2000", "Rs. 2000".
# The lookbehind keeps English words that merely end in "rs" ("farmers 20")
# from being read as currency.
_CURRENCY_PREFIX_RE = re.compile(r"(?<![a-z0-9])(₹|రూ|inr|rs)\s*[.,]?\s*$", re.IGNORECASE)
# Markers that may sit right after the amount: "20 rupees", "2000 రూపాయలు".
_CURRENCY_SUFFIX_RE = re.compile(
    r"(rupees|rupee|రూపాయలు|రూ|inr|rs\.?)\b", re.IGNORECASE
)
# "20 per kg" also signals a per-unit price.
_PER_UNIT_RE = re.compile(r"per\b", re.IGNORECASE)


def _ends_with_currency_prefix(before: str) -> bool:
    return _CURRENCY_PREFIX_RE.search(before) is not None


def extract_price(
    text: str, skip_spans: Iterable[tuple[int, int]] = ()
) -> int | None:
    """First amount with an explicit currency marker or ``per <unit>`` → paise.

    Numbers whose span appears in ``skip_spans`` (the quantity number) are
    ignored. Without a marker nothing is extracted — a bare number is never
    guessed to be a price.
    """
    for match in _NUMBER_RE.finditer(text):
        if any(start <= match.start() < end for start, end in skip_spans):
            continue
        after = text[match.end() :].lstrip()
        if (
            _ends_with_currency_prefix(text[: match.start()])
            or _CURRENCY_SUFFIX_RE.match(after)
            or _PER_UNIT_RE.match(after)
        ):
            rupees = float(match.group())
            return int(round(rupees * 100))
    return None


# --- Relative availability dates ----------------------------------------------

# (phrases, offset in days). "ఎల్లుడు" literally means yesterday, but in
# supply-availability talk ("ఎల్లుడు నుంచి అందుబాటులో") it is used for the
# day after — mapped per the voice-listing spec.
_RELATIVE_DAYS: tuple[tuple[tuple[str, ...], int], ...] = (
    (("day after tomorrow", "day after", "ఎల్లుడు"), 2),
    (("tomorrow", "రేపు"), 1),
    (("today", "ఈరోజు", "ఈ రోజు"), 0),
)


def extract_available_from(text: str, today: date | None = None) -> date | None:
    """Named relative day → concrete ISO date, else ``None``.

    The earliest mention wins; at the same position the longest phrase wins
    ("day after tomorrow" over "day after").
    """
    best: tuple[int, int, int] | None = None  # (position, -length, offset)
    for phrases, offset in _RELATIVE_DAYS:
        for phrase in phrases:
            idx = text.find(phrase)
            while idx != -1:
                candidate = (idx, -len(phrase), offset)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
                idx = text.find(phrase, idx + 1)
    if best is None:
        return None
    return (today or date.today()) + timedelta(days=best[2])


# --- Commodity matching -------------------------------------------------------

# Transcript-side aliases → canonical (lower-cased) English commodity name.
SYNONYMS: dict[str, str] = {
    # tomato
    "tamata": "tomato",
    "tamatar": "tomato",
    "టమాటా": "tomato",
    "टमाटर": "tomato",
    # onion
    "ulli": "onion",
    "ullipayalu": "onion",
    "ఉల్లి": "onion",
    "ఉల్లిపాయలు": "onion",
    "pyaz": "onion",
    "प्याज": "onion",
    # potato
    "alugadda": "potato",
    "aloo": "potato",
    "ఆలుగడ్డ": "potato",
    "బంగాళదుంప": "potato",
    "आलू": "potato",
    # banana
    "arati": "banana",
    "అరటి": "banana",
    "केला": "banana",
    # staples
    "biyyam": "rice",
    "బియ్యం": "rice",
    "వరి": "rice",
    "चावल": "rice",
    "godhuma": "wheat",
    "గోధుమలు": "wheat",
    "గోధుమ": "wheat",
    "गेहूं": "wheat",
    "mokkajonna": "maize",
    "మొక్కజొన్న": "maize",
    "मक्का": "maize",
}

# Confidence per match kind: official catalogue name vs synonym.
_EXACT_CONFIDENCE = 1.0
_SYNONYM_CONFIDENCE = 0.8

# Latin aliases need word-ish boundaries so "ulli" cannot match inside
# "sullied"; other scripts have no such collisions, plain find is fine.
_LATIN_ALIAS_RE = re.compile(r"(?<![a-z0-9])(?P<alias>[a-z0-9]+)(?![a-z0-9])")


def _find_alias(text: str, alias: str) -> int | None:
    """Position of `alias` in `text`, or None. Text must be lower-cased."""
    if alias.isascii():
        for match in _LATIN_ALIAS_RE.finditer(text):
            if match.group("alias") == alias:
                return match.start()
        return None
    position = text.find(alias)
    return position if position != -1 else None


def match_commodity(
    text: str, commodities: Iterable[Any]
) -> dict | None:
    """Best catalogue match for the transcript, or ``None``.

    ``commodities``: rows exposing ``id, name_en, name_te, name_hi`` (ORM
    objects or any duck-typed stand-in). A hit on an official
    ``name_en/name_te/name_hi`` scores 1.0, a synonym hit 0.8; the longest
    matched name wins, ties broken by earliest position.
    """
    text = (text or "").lower()
    best_key: tuple[int, int, float] | None = None
    best_row: Any = None
    best_confidence = 0.0

    for row in commodities:
        canonical = str(getattr(row, "name_en", "") or "").strip().lower()
        if not canonical:
            continue
        candidates: list[tuple[str, float]] = [
            (canonical, _EXACT_CONFIDENCE)
        ]
        for name in (getattr(row, "name_te", None), getattr(row, "name_hi", None)):
            name = str(name or "").strip()
            if name:
                candidates.append((name.lower(), _EXACT_CONFIDENCE))
        for alias, target in SYNONYMS.items():
            if target == canonical:
                candidates.append((alias.lower(), _SYNONYM_CONFIDENCE))

        for candidate, confidence in candidates:
            position = _find_alias(text, candidate)
            if position is None:
                continue
            key = (len(candidate), -position, confidence)
            if best_key is None or key > best_key:
                best_key, best_row, best_confidence = key, row, confidence

    if best_row is None:
        return None
    return {
        "id": best_row.id,
        "name_en": best_row.name_en,
        "confidence": best_confidence,
    }


# --- Full extraction ------------------------------------------------------------

_CONFIRMED_FIELDS = (
    ("commodity", lambda e: e["commodity"]),
    ("quantity", lambda e: e["quantity"]),
    ("unit", lambda e: e["unit"]),
    ("price", lambda e: e["price_paise"]),
    ("available_from", lambda e: e["available_from"]),
)


def extract_listing_fields(
    text: str,
    commodities: Iterable[Any],
    *,
    today: date | None = None,
) -> dict:
    """Extract every supported field from one transcript.

    Returns a dict shaped like the API's ``extracted`` object plus an overall
    ``confidence`` (the lowest confidence among the detected fields, 0.0 when
    nothing was detected). Missing values stay ``None`` — never guessed.
    """
    text = normalize_digits((text or "").lower())
    quantity, unit, quantity_span = extract_quantity(text)
    price_paise = extract_price(
        text, skip_spans=(quantity_span,) if quantity_span else ()
    )
    available_from = extract_available_from(text, today=today)
    commodity = match_commodity(text, commodities)

    confidences = [
        float(part["confidence"]) if isinstance(part, dict) else _EXACT_CONFIDENCE
        for part in (commodity, quantity, unit, price_paise, available_from)
        if part is not None
    ]

    return {
        "commodity": commodity,
        "quantity": quantity,
        "unit": unit,
        "price_paise": price_paise,
        "available_from": available_from,
        "confidence": round(min(confidences), 2) if confidences else 0.0,
    }


def fields_needing_confirmation(extracted: dict) -> list[str]:
    """Names of the fields the farmer must confirm because they are missing."""
    return [name for name, get in _CONFIRMED_FIELDS if get(extracted) is None]
