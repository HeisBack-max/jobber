"""Application tracking + feedback persistence (spec §37/§38)."""

from __future__ import annotations

import asyncio

from tests.test_pipeline_db import FakeSource, _raw_job


def test_application_status_and_feedback_round_trip(temp_db, monkeypatch):
    from jobintel import pipeline

    fake = FakeSource([_raw_job()])
    monkeypatch.setattr(pipeline, "build_sources", lambda: [fake])
    asyncio.run(pipeline.run_collection())

    from jobintel.db.models import ApplicationStatusRecord, Feedback, Job

    with temp_db.session_scope() as session:
        job = session.query(Job).first()
        job_id = job.id
        session.add(ApplicationStatusRecord(job_id=job_id, status="Interested"))
        session.add(ApplicationStatusRecord(job_id=job_id, status="Applied", notes="Tailored CV sent."))
        session.add(Feedback(job_id=job_id, reaction="EXCELLENT_MATCH"))

    with temp_db.session_scope() as session:
        statuses = session.query(ApplicationStatusRecord).filter_by(job_id=job_id).all()
        assert [s.status for s in statuses] == ["Interested", "Applied"]
        assert statuses[1].notes == "Tailored CV sent."

        feedback = session.query(Feedback).filter_by(job_id=job_id).all()
        assert feedback[0].reaction == "EXCELLENT_MATCH"
