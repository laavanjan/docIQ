"""document_images table

Revision ID: 0002_document_images
Revises: 0001_initial
Create Date: 2026-05-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_document_images"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("image_index", sa.Integer(), server_default="0"),
        sa.Column("ext", sa.String(length=8), server_default="png"),
        sa.Column("width", sa.Integer(), server_default="0"),
        sa.Column("height", sa.Integer(), server_default="0"),
        sa.Column("sha256", sa.String(length=64)),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_images_document_id", "document_images", ["document_id"])
    op.create_index("ix_document_images_owner_id", "document_images", ["owner_id"])
    op.create_index("ix_document_images_page_number", "document_images", ["page_number"])
    op.create_index("ix_document_images_sha256", "document_images", ["sha256"])


def downgrade() -> None:
    op.drop_table("document_images")
