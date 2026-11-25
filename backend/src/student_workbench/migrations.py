"""Lightweight, idempotent schema upgrades for the local SQLite database.

The app has no migration framework: the database is a single local file and
``Base.metadata.create_all`` only creates *missing tables*. A column added to an
existing model therefore needs an explicit ``ALTER TABLE``, which this module
applies once and records nothing — the column list itself is the source of
truth, so re-running is a no-op.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# table -> {column: SQLite column type}
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "course_schedule_entries": {
        "period_start": "INTEGER",
        "period_end": "INTEGER",
    },
    "settings": {
        "portal_week": "INTEGER",
        "portal_week_checked_on": "DATE",
    },
    "repo_snapshots": {
        "github_json": "TEXT",
        "github_error": "TEXT",
    },
}


def ensure_schema(engine: Engine) -> list[str]:
    """Add model columns that are missing from an already-created table."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    applied: list[str] = []
    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            # create_all builds it with every column already.
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        missing = {name: ddl for name, ddl in columns.items() if name not in present}
        if not missing:
            continue
        with engine.begin() as connection:
            for name, ddl in missing.items():
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                )
                applied.append(f"{table}.{name}")
    return applied
