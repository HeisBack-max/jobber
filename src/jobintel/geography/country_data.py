"""Country/region reference data for the deterministic geography engine.

Deliberately conservative and hand-curated rather than exhaustive - the
classifier's job is to be right about US/Thailand exclusion and about
Richard's remote-priority tiers, not to resolve every country on earth.
Unrecognized country names fall through to UNCLEAR, which routes to
manual review rather than a guessed eligibility.
"""

from __future__ import annotations

US_NAMES = {
    "united states", "usa", "u.s.a.", "u.s.", "us", "united states of america",
    "the united states", "america",
}

THAILAND_NAMES = {
    "thailand", "th", "kingdom of thailand", "bangkok",
}

UK_NAMES = {
    "united kingdom", "uk", "u.k.", "great britain", "england", "scotland",
    "wales", "northern ireland",
}

CANADA_NAMES = {"canada", "ca"}

EUROPE_COUNTRIES = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic", "czechia",
    "denmark", "estonia", "finland", "france", "germany", "greece", "hungary",
    "iceland", "ireland", "italy", "latvia", "liechtenstein", "lithuania",
    "luxembourg", "malta", "netherlands", "norway", "poland", "portugal",
    "romania", "slovakia", "slovenia", "spain", "sweden", "switzerland",
    "united kingdom", "uk",
}

EMEA_EXTRA_COUNTRIES = {
    "south africa", "nigeria", "kenya", "egypt", "morocco", "israel", "turkey", "türkiye",
}

MIDDLE_EAST_COUNTRIES = {
    "united arab emirates", "uae", "qatar", "saudi arabia", "kuwait", "bahrain",
    "oman", "jordan", "lebanon", "israel", "turkey", "türkiye", "iraq",
}

ASIA_COUNTRIES_EXCLUDING_THAILAND = {
    "japan", "south korea", "korea", "singapore", "malaysia", "indonesia", "vietnam",
    "philippines", "india", "china", "taiwan", "hong kong", "cambodia", "laos",
    "myanmar", "bangladesh", "sri lanka", "pakistan", "kazakhstan", "azerbaijan",
    "uzbekistan",
}

APAC_COUNTRIES_EXCLUDING_THAILAND = ASIA_COUNTRIES_EXCLUDING_THAILAND | {
    "australia", "new zealand",
}

ALL_KNOWN_COUNTRIES = (
    US_NAMES | THAILAND_NAMES | UK_NAMES | CANADA_NAMES | EUROPE_COUNTRIES
    | EMEA_EXTRA_COUNTRIES | MIDDLE_EAST_COUNTRIES | APAC_COUNTRIES_EXCLUDING_THAILAND
)

REGULAR_TRAVEL_FREQUENCY_TERMS = {
    "weekly", "biweekly", "bi-weekly", "monthly", "quarterly", "every month",
    "each month", "regularly", "frequently", "routine", "routinely", "ongoing basis",
    "ongoing travel", "ongoing", "~monthly", "several times a year", "recurring",
}

OCCASIONAL_TRAVEL_FREQUENCY_TERMS = {
    "occasionally", "occasional", "rarely", "as needed", "annually", "once a year",
    "a few times a year", "infrequent", "infrequently", "on rare occasions",
}
