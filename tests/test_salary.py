from __future__ import annotations

from jobintel.normalize.salary import parse_salary


def test_missing_salary_is_unknown_not_zero():
    parsed = parse_salary(None)
    assert parsed.salary_min is None
    assert parsed.salary_max is None


def test_gbp_range_annual():
    parsed = parse_salary("£85,000 - £105,000 per year")
    assert parsed.salary_currency == "GBP"
    assert parsed.salary_period == "annual"
    assert parsed.salary_min == 85000
    assert parsed.salary_max == 105000


def test_usd_hourly_range():
    parsed = parse_salary("$65-90/hour")
    assert parsed.salary_currency == "USD"
    assert parsed.salary_period == "hourly"
    assert parsed.salary_min == 65
    assert parsed.salary_max == 90


def test_single_value_salary():
    parsed = parse_salary("$120,000 annually")
    assert parsed.salary_min == 120000
    assert parsed.salary_max == 120000


def test_k_suffix_expanded():
    parsed = parse_salary("$90k - $110k per year")
    assert parsed.salary_min == 90000
    assert parsed.salary_max == 110000
