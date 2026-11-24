from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

DATA_DIR_ENV = "STUDENT_WORKBENCH_DATA_DIR"
DB_URL_ENV = "STUDENT_WORKBENCH_DB_URL"
TIMEZONE_ENV = "STUDENT_WORKBENCH_TIMEZONE"


def _project_root() -> Path | None:
    """Return the repository root when running from a source checkout."""
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "backend").is_dir() and (candidate / "frontend").is_dir():
        return candidate
    return None


def _default_data_dir() -> Path:
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    root = _project_root()
    if root is not None:
        # Keep runtime state next to the code so it is easy to inspect with a
        # SQLite client. ``data/`` is git-ignored.
        return root / "data"
    return Path(platformdirs.user_data_dir("student-workbench", appauthor=False))


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path = field(default_factory=_default_data_dir)
    db_url: str | None = None
    timezone: str = "Asia/Shanghai"

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", Path(self.data_dir))

    @property
    def resolved_db_url(self) -> str:
        if self.db_url:
            return self.db_url
        return f"sqlite:///{(self.data_dir / 'workbench.db').as_posix()}"

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            data_dir=_default_data_dir(),
            db_url=os.environ.get(DB_URL_ENV),
            timezone=os.environ.get(TIMEZONE_ENV, "Asia/Shanghai"),
        )
