"""initial persistence schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. investigations table
    op.create_table(
        'investigations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cluster_context', sa.String(length=100), nullable=True),
        sa.Column('namespace', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('confidence_level', sa.String(length=20), nullable=True),
        sa.Column('suggested_fix', sa.Text(), nullable=True),
        sa.Column('kubectl_commands', sa.JSON(), nullable=True),
        sa.Column('yaml_proposal', sa.Text(), nullable=True),
        sa.Column('prevention_recommendations', sa.JSON(), nullable=True),
        sa.Column('evidence_gaps', sa.JSON(), nullable=True),
        sa.Column('raw_evidence', sa.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('fingerprint_hash', sa.String(length=64), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_investigations_user_id'), 'investigations', ['user_id'], unique=False)
    op.create_index(op.f('ix_investigations_namespace'), 'investigations', ['namespace'], unique=False)
    op.create_index(op.f('ix_investigations_status'), 'investigations', ['status'], unique=False)
    op.create_index(op.f('ix_investigations_created_at'), 'investigations', ['created_at'], unique=False)
    op.create_index(op.f('ix_investigations_fingerprint_hash'), 'investigations', ['fingerprint_hash'], unique=False)

    # 3. findings table
    op.create_table(
        'findings',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('investigation_id', sa.String(), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('resource_kind', sa.String(length=50), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('namespace', sa.String(length=100), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('evidence_detail', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_findings_investigation_id'), 'findings', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_findings_category'), 'findings', ['category'], unique=False)

    # 4. incident_fingerprints table
    op.create_table(
        'incident_fingerprints',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('fingerprint_hash', sa.String(length=64), nullable=False),
        sa.Column('failure_category', sa.String(length=100), nullable=False),
        sa.Column('resource_kind', sa.String(length=50), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('namespace', sa.String(length=100), nullable=True),
        sa.Column('first_observed_at', sa.DateTime(), nullable=True),
        sa.Column('last_observed_at', sa.DateTime(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=True, default=1),
        sa.Column('last_investigation_id', sa.String(length=64), nullable=True),
    )
    op.create_index(op.f('ix_incident_fingerprints_fingerprint_hash'), 'incident_fingerprints', ['fingerprint_hash'], unique=True)
    op.create_index(op.f('ix_incident_fingerprints_user_id'), 'incident_fingerprints', ['user_id'], unique=False)
    op.create_index(op.f('ix_incident_fingerprints_namespace'), 'incident_fingerprints', ['namespace'], unique=False)


def downgrade() -> None:
    op.drop_table('incident_fingerprints')
    op.drop_table('findings')
    op.drop_table('investigations')
    op.drop_table('users')
