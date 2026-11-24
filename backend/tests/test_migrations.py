from __future__ import annotations

from sqlalchemy import create_engine, text

from student_workbench.migrations import ensure_schema


def test_ensure_schema_adds_missing_period_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE course_schedule_entries ("
                "id VARCHAR(36) PRIMARY KEY, start_time VARCHAR(5), end_time VARCHAR(5))"
            )
        )

    applied = ensure_schema(engine)

    assert sorted(applied) == [
        "course_schedule_entries.period_end",
        "course_schedule_entries.period_start",
    ]
    columns = {row[1] for row in engine.connect().execute(
        text("PRAGMA table_info(course_schedule_entries)")
    )}
    assert {"period_start", "period_end"} <= columns


def test_ensure_schema_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE course_schedule_entries (id VARCHAR(36) PRIMARY KEY)")
        )

    assert len(ensure_schema(engine)) == 2
    assert ensure_schema(engine) == []


def test_ensure_schema_skips_missing_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    assert ensure_schema(engine) == []
