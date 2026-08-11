"""Salary normalization (spec §48). Missing compensation is represented
as UNKNOWN (all fields None), never zero."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY"}
_CURRENCY_CODES = {"usd", "gbp", "eur", "jpy", "cad", "aud", "chf", "sgd", "aed"}

_PERIOD_TERMS = {
    "hour": "hourly", "hr": "hourly", "hourly": "hourly",
    "day": "daily", "daily": "daily",
    "month": "monthly", "monthly": "monthly",
    "year": "annual", "yr": "annual", "annum": "annual", "annual": "annual", "annually": "annual",
}

_NUMBER_RE = r"([\d,]+(?:\.\d+)?)\s*[kK]?"


@dataclass
class ParsedSalary:
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None


def _to_number(raw: str, had_k_suffix: bool) -> float:
    value = float(raw.replace(",", ""))
    return value * 1000 if had_k_suffix else value


def parse_salary(raw_text: str | None) -> ParsedSalary:
    if not raw_text:
        return ParsedSalary()

    text = raw_text.strip()
    currency = None
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            currency = code
            break
    if currency is None:
        lower = text.lower()
        for code in _CURRENCY_CODES:
            if re.search(rf"\b{code}\b", lower):
                currency = code.upper()
                break

    period = None
    lower = text.lower()
    for term, label in _PERIOD_TERMS.items():
        if re.search(rf"\b{term}s?\b", lower):
            period = label
            break

    numbers = re.findall(rf"{_NUMBER_RE}", text)
    has_k = bool(re.search(r"\d\s*[kK]\b", text))
    values = [_to_number(n, has_k) for n in numbers if n]

    if not values:
        return ParsedSalary(salary_currency=currency, salary_period=period)
    if len(values) == 1:
        return ParsedSalary(salary_min=values[0], salary_max=values[0], salary_currency=currency, salary_period=period)

    return ParsedSalary(
        salary_min=min(values[:2]), salary_max=max(values[:2]),
        salary_currency=currency, salary_period=period,
    )
