from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from db.connection import database_url

# Migrations are hand-written (additive-only per plan §4.3); no model metadata.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=database_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # psycopg3 driver spelling for SQLAlchemy
    url = database_url().replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
