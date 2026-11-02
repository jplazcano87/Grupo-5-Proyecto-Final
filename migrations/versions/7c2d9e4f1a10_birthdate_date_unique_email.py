"""store birthdate as a date and make email unique

Revision ID: 7c2d9e4f1a10
Revises: 1794211427b9
Create Date: 2026-11-02 12:00:00.000000

Before upgrading a database that already has users, make sure no two users
share an email, otherwise creating the unique index fails.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c2d9e4f1a10'
down_revision = '1794211427b9'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite already stores dates as ISO-8601 text, which SQLAlchemy's Date reads
    # as-is. Rebuilding the table to retype the column would CAST the text to
    # DATE (numeric affinity) and truncate '1990-05-17' to 1990, so skip it there.
    if op.get_bind().dialect.name != 'sqlite':
        op.alter_column(
            'users',
            'birthdate',
            existing_type=sa.Text(),
            type_=sa.Date(),
            existing_nullable=False,
            postgresql_using='birthdate::date',
        )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade():
    op.drop_index('ix_users_email', table_name='users')
    if op.get_bind().dialect.name != 'sqlite':
        op.alter_column(
            'users',
            'birthdate',
            existing_type=sa.Date(),
            type_=sa.Text(),
            existing_nullable=False,
        )
