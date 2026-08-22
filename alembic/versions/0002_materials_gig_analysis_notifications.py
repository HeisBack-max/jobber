"""application_materials, gig_analysis and notification_log

Adds the three tables the completed feature set needs:

* `gig_analysis` - gig scoring components (promised in
  IMPLEMENTATION_PLAN.md §4 but never created; gigs previously kept only
  a single opaque `gigs.gig_quality_score` with no breakdown, which
  violates the "no unexplained magic scores" rule).
* `application_materials` - generated CV-tailoring briefs and cover
  letters, with the cv_evidence_map ids each was built from so any claim
  stays auditable back to the real CV.
* `notification_log` - one row per delivery attempt, so an urgent alert
  fires exactly once per job however often the pipeline runs.

Revision ID: 0002
Revises: 0001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gig_analysis",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("gig_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("gig_quality_score", sa.Float(), nullable=False),
        sa.Column("geographic_compatibility", sa.Float(), nullable=False),
        sa.Column("professional_relevance", sa.Float(), nullable=False),
        sa.Column("compensation", sa.Float(), nullable=False),
        sa.Column("flexibility", sa.Float(), nullable=False),
        sa.Column("ai_cyber_career_value", sa.Float(), nullable=False),
        sa.Column("source_reliability", sa.Float(), nullable=False),
        sa.Column("time_commitment_compatibility", sa.Float(), nullable=False),
        sa.Column("is_commodity_annotation", sa.Boolean(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["gig_id"], ["gigs.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gig_analysis_gig_quality_score"), "gig_analysis", ["gig_quality_score"], unique=False)

    op.create_table(
        "application_materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("unsupported_requirements", sa.JSON(), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_log_job_id"), "notification_log", ["job_id"], unique=False)
    op.create_index(op.f("ix_notification_log_kind"), "notification_log", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_log_kind"), table_name="notification_log")
    op.drop_index(op.f("ix_notification_log_job_id"), table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_table("application_materials")
    op.drop_index(op.f("ix_gig_analysis_gig_quality_score"), table_name="gig_analysis")
    op.drop_table("gig_analysis")
