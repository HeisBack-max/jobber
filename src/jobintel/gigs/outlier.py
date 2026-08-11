"""Outlier AI gig source - INTENTIONALLY NOT IMPLEMENTED.

Outlier AI (and comparable expert-marketplace platforms: RLHF providers,
model-training/evaluation networks) do not expose an unauthenticated,
public listing API. Their project listings only become visible after
account login. Building a scraper against an authenticated session would
require storing Richard's credentials in this application and would risk
violating the platform's Terms of Service - both are outside this app's
threat model and the spec's explicit prohibition on bypassing
authentication/access controls (spec §29/§47/§65).

This class exists so the GigSource interface has a concrete, documented
example, and so the dashboard's source-health panel can show Outlier as
"NOT_IMPLEMENTED - requires ToS-compliant access" instead of silently
omitting it. It never performs a network request.

To make this real in the future: Richard would need to either (a) get
explicit written confirmation from Outlier that programmatic collection
against his own logged-in account is permitted and provide a way to
supply session credentials safely (e.g. a manually-refreshed session
cookie via an environment variable, never committed), or (b) use an
official partner/API integration if Outlier ever publishes one.
"""

from __future__ import annotations

from jobintel.gigs.base import GigSource, RawGigDetails
from jobintel.models.schemas import RawJob


class OutlierGigSourceNotImplemented(GigSource):
    name = "outlier"
    platform_reliability = 0.6

    async def discover(self) -> list[RawJob]:
        raise NotImplementedError(
            "Outlier AI requires authenticated access; no public listing API exists. "
            "See jobintel/gigs/outlier.py module docstring for what would be required "
            "to implement this in a ToS-compliant way."
        )

    async def fetch_details(self, job: RawJob) -> RawGigDetails:
        raise NotImplementedError("See discover().")
