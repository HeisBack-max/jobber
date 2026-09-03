"""Streamlit dashboard - the only UI Richard needs (spec §40-42).

Reads only from the database; never talks to a collector/source directly
(see ARCHITECTURE.md §4). Run with `jobintel dashboard` or
`streamlit run dashboard/app.py`.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobintel.db.models import (  # noqa: E402
    ApplicationStatusRecord,
    Feedback,
    Gig,
    Job,
    JobAnalysisRecord,
    SourceHealthRecord,
)
from jobintel.db.session import session_scope  # noqa: E402
from jobintel.discovery.strategic_watch import get_strategic_coverage  # noqa: E402
from jobintel.settings import load_roles, load_strategic_companies  # noqa: E402

st.set_page_config(page_title="Remote Job Intelligence", layout="wide", page_icon="🧭")

REMOTE_EMOJI = {
    "REMOTE_WORLDWIDE": "🌍 Remote Worldwide",
    "REMOTE_ANYWHERE_WITH_MINOR_TIMEZONE_LIMIT": "🌍 Remote (minor timezone limit)",
    "REMOTE_UK": "🇬🇧 Remote UK",
    "REMOTE_EUROPE": "🇪🇺 Remote Europe",
    "REMOTE_EMEA": "🌍 Remote EMEA",
    "REMOTE_APAC": "🌏 Remote APAC",
    "REMOTE_ASIA": "🌏 Remote Asia",
    "REMOTE_MIDDLE_EAST": "🌍 Remote Middle East",
    "REMOTE_WITH_OCCASIONAL_TRAVEL": "✈️ Remote (occasional travel)",
    "REMOTE_CANADA_ONLY": "🇨🇦 Remote Canada only",
    "REMOTE_US_ONLY": "🇺🇸 Remote US only (EXCLUDED)",
    "REMOTE_THAILAND_ONLY": "🇹🇭 Remote Thailand only (EXCLUDED)",
    "HYBRID": "🏢 Hybrid",
    "ONSITE": "🏢 Onsite",
    "UNCLEAR": "❓ Unclear",
}

ACTION_STATUSES = ["Interested", "Applied", "Not Interested"]


def _utcnow_naive() -> datetime:
    """SQLite round-trips DATETIME columns as naive; all "now" values used
    to compare against DB-sourced datetimes must match that shape."""
    return datetime.now(UTC).replace(tzinfo=None)


@st.cache_data(ttl=30)
def _strategic_company_names() -> set[str]:
    data = load_strategic_companies()
    names = set()
    for tier in data.get("tiers", {}).values():
        for company in tier.get("companies", []):
            names.add(company["name"].strip().lower())
    return names


@st.cache_data(ttl=30)
def _role_family_options() -> list[str]:
    return sorted(load_roles().get("role_families", {}).keys())


def _fetch_rows(session, filters: dict):
    query = session.query(Job, JobAnalysisRecord).join(JobAnalysisRecord, JobAnalysisRecord.job_id == Job.id)

    if filters["min_score"] > 0:
        query = query.filter(JobAnalysisRecord.overall_score >= filters["min_score"])
    if filters["recommendation"] != "Any":
        query = query.filter(JobAnalysisRecord.recommendation == filters["recommendation"])
    if filters["keyword"]:
        like = f"%{filters['keyword'].lower()}%"
        query = query.filter(Job.job_title.ilike(like) | Job.job_description_clean.ilike(like))
    if filters["employer"]:
        query = query.filter(Job.company_name.ilike(f"%{filters['employer']}%"))
    if filters["role_family"] != "Any":
        query = query.filter(Job.role_family == filters["role_family"])
    if filters["remote_classification"] != "Any":
        query = query.filter(Job.remote_classification == filters["remote_classification"])
    if filters["geo_eligibility"] != "Any":
        query = query.filter(Job.candidate_geographically_eligible == filters["geo_eligibility"])
    if filters["opportunity_class"] != "Any":
        query = query.filter(Job.opportunity_class == filters["opportunity_class"])
    if filters["since_last_visit"] and filters["last_visit"] is not None:
        query = query.filter(Job.first_seen_at >= filters["last_visit"])

    query = query.order_by(JobAnalysisRecord.overall_score.desc())
    return query.limit(300).all()


def _render_card(job: Job, analysis: JobAnalysisRecord, is_strategic: bool, key_prefix: str) -> None:
    remote_label = REMOTE_EMOJI.get(job.remote_classification, job.remote_classification)
    posted = job.published_at or job.first_seen_at
    posted_str = "unknown" if posted is None else _humanize_age(posted)
    salary = "Salary: UNKNOWN"
    if job.salary_min or job.salary_max:
        cur = job.salary_currency or ""
        lo = f"{job.salary_min:,.0f}" if job.salary_min else "?"
        hi = f"{job.salary_max:,.0f}" if job.salary_max else "?"
        salary = f"💰 {cur} {lo}-{hi} ({job.salary_period or 'period unspecified'})"

    strategic_badge = " ⭐ STRATEGIC" if is_strategic else ""
    with st.container(border=True):
        st.markdown(f"### {analysis.overall_score:.0f} — {analysis.recommendation}{strategic_badge}")
        st.markdown(f"**{job.job_title}** — {job.company_name}")
        st.caption(f"{remote_label}  ·  🕐 Posted {posted_str}  ·  {salary}")

        if analysis.strengths:
            st.markdown("**Why you fit**")
            for s in analysis.strengths[:4]:
                st.markdown(f"- {s}")
        if analysis.concerns or analysis.preferred_gaps:
            st.markdown("**Potential gaps**")
            for c in (analysis.concerns + analysis.preferred_gaps)[:3]:
                st.markdown(f"- {c}")
        if analysis.mandatory_mismatches:
            st.markdown("**Mandatory mismatches**")
            for m in analysis.mandatory_mismatches:
                st.markdown(f"- ⚠️ {m}")

        st.markdown(f"**Geography:** {job.candidate_geographically_eligible} · **Readiness:** {analysis.application_readiness}")
        st.progress(min(1.0, analysis.confidence_score / 100), text=f"Confidence: {analysis.confidence_score:.0f}%")

        cols = st.columns(5)
        cols[0].link_button("Open Job", job.canonical_url or job.source_url, width='stretch')
        for i, status in enumerate(ACTION_STATUSES, start=1):
            if cols[i].button(status, key=f"{key_prefix}-{job.id}-{status}", width='stretch'):
                _set_application_status(job.id, status)
                st.toast(f"Marked as {status}")
        with cols[4].popover("Explain Match", width='stretch'):
            st.write(analysis.reasoning_summary)
            st.markdown("**Geographic evidence:**")
            for e in analysis.geographic_evidence:
                st.markdown(f"- {e}")

        fb_cols = st.columns(4)
        reactions = [("👍 Excellent", "EXCELLENT_MATCH"), ("👌 Relevant", "RELEVANT"),
                     ("👎 Not interested", "NOT_INTERESTED"), ("🚫 Never show like this", "NEVER_SHOW_LIKE_THIS")]
        for col, (label, value) in zip(fb_cols, reactions, strict=False):
            if col.button(label, key=f"{key_prefix}-{job.id}-fb-{value}"):
                _record_feedback(job.id, value)
                st.toast("Feedback recorded")


def _humanize_age(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    hours = delta.total_seconds() / 3600
    if hours < 24:
        return f"{hours:.0f} hours ago"
    days = hours / 24
    return f"{days:.0f} days ago"


def _set_application_status(job_id: str, status: str) -> None:
    with session_scope() as session:
        session.add(ApplicationStatusRecord(job_id=job_id, status=status))


def _record_feedback(job_id: str, reaction: str) -> None:
    with session_scope() as session:
        session.add(Feedback(job_id=job_id, reaction=reaction))


def main() -> None:
    st.title("🧭 Remote Job Intelligence")
    st.caption("Richard Best's personal opportunity analyst")

    if "last_visit" not in st.session_state:
        st.session_state["last_visit"] = _utcnow_naive() - timedelta(days=1)

    with st.sidebar:
        st.header("Filters")
        min_score = st.slider("Minimum score", 0, 100, 0)
        recommendation = st.selectbox(
            "Recommendation", ["Any", "EXCEPTIONAL_MATCH", "STRONG_APPLY", "WORTH_REVIEWING",
                                "STRETCH_OPPORTUNITY", "LOW_PRIORITY", "IGNORE", "INELIGIBLE",
                                "EXCLUDED_TRAVEL_REQUIREMENT"],
        )
        keyword = st.text_input("Keyword")
        employer = st.text_input("Employer")
        role_family = st.selectbox("Role family", ["Any"] + _role_family_options())
        remote_classification = st.selectbox("Remote classification", ["Any"] + list(REMOTE_EMOJI.keys()))
        geo_eligibility = st.selectbox("Geographic eligibility", ["Any", "YES", "NO", "UNCLEAR"])
        opportunity_class = st.selectbox(
            "Opportunity class",
            ["Any", "PERMANENT_EMPLOYMENT", "FIXED_TERM_CONTRACT", "CONSULTING", "FREELANCE",
             "SHORT_PROJECT", "GIG_PROJECT_WORK", "UNIVERSITY_TEACHING", "OTHER"],
        )
        since_last_visit = st.checkbox("Show only opportunities added since my last visit")

    filters = dict(
        min_score=min_score, recommendation=recommendation, keyword=keyword, employer=employer,
        role_family=role_family, remote_classification=remote_classification,
        geo_eligibility=geo_eligibility, opportunity_class=opportunity_class,
        since_last_visit=since_last_visit, last_visit=st.session_state["last_visit"],
    )

    strategic_names = _strategic_company_names()

    tabs = st.tabs([
        "Best Matches Today", "True Remote", "Frontier AI / Strategic", "Vertex AI & Gemini",
        "Gigs & Quicker Income", "Interesting Wildcards", "Newly Discovered", "Source Health",
    ])

    with session_scope() as session:
        rows = _fetch_rows(session, filters)

        with tabs[0]:
            best = [r for r in rows if r[1].recommendation in ("EXCEPTIONAL_MATCH", "STRONG_APPLY")]
            _render_feed(best, strategic_names, "best")

        with tabs[1]:
            true_remote = [r for r in rows if r[0].remote_classification.startswith("REMOTE_") and r[0].candidate_geographically_eligible == "YES"]
            _render_feed(true_remote, strategic_names, "remote")

        with tabs[2]:
            strategic = [r for r in rows if r[0].company_name.strip().lower() in strategic_names]
            _render_feed(strategic, strategic_names, "strategic")

        with tabs[3]:
            vertex = [r for r in rows if r[0].role_family == "google_vertex_ai" or "vertex" in (r[0].job_description_clean or "").lower() or "gemini" in (r[0].job_description_clean or "").lower()]
            _render_feed(vertex, strategic_names, "vertex")

        with tabs[4]:
            gigs = (
                session.query(Job, JobAnalysisRecord, Gig)
                .join(JobAnalysisRecord, JobAnalysisRecord.job_id == Job.id)
                .join(Gig, Gig.job_id == Job.id)
                .order_by(Gig.gig_quality_score.desc())
                .limit(50)
                .all()
            )
            if not gigs:
                st.info(
                    "No gig/project opportunities collected yet. See IMPLEMENTATION_PLAN.md "
                    "for gig-source status (e.g. Outlier AI requires ToS-compliant "
                    "authenticated access, not yet implemented)."
                )
            for job, analysis, _gig in gigs:
                _render_card(job, analysis, False, "gig")

        with tabs[5]:
            wildcards = [
                r for r in rows
                if r[0].role_family not in ("ai_training", "cybersecurity_training", None)
                and r[1].overall_score >= 70
            ]
            _render_feed(wildcards, strategic_names, "wildcard")

        with tabs[6]:
            newly = [r for r in rows if r[0].first_seen_at and r[0].first_seen_at >= _utcnow_naive() - timedelta(days=2)]
            _render_feed(newly, strategic_names, "new")

        with tabs[7]:
            st.subheader("Strategic company coverage")
            coverage = get_strategic_coverage()
            st.dataframe(
                [{"Company": c.name, "Tier": c.tier, "ATS": c.ats, "Live collector": c.has_live_collector,
                  "Verification": c.verification_status, "Notes": c.notes} for c in coverage],
                width='stretch',
            )
            st.subheader("Last collection run per source")
            health_rows = session.query(SourceHealthRecord).order_by(SourceHealthRecord.run_started_at.desc()).limit(50).all()
            st.dataframe(
                [{"Source": h.source, "Status": h.status, "Jobs discovered": h.jobs_discovered,
                  "Started": h.run_started_at, "Errors": h.errors} for h in health_rows],
                width='stretch',
            )

    st.session_state["last_visit"] = _utcnow_naive()


def _render_feed(rows, strategic_names, key_prefix: str) -> None:
    if not rows:
        st.info("No opportunities match the current filters.")
        return
    for job, analysis in rows:
        is_strategic = job.company_name.strip().lower() in strategic_names
        _render_card(job, analysis, is_strategic, key_prefix)


if __name__ == "__main__":
    main()
