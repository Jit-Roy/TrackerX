from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def app_data_dir() -> Path:
    base = Path.home() / ".trackerx"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path = app_data_dir()

    @property
    def database_path(self) -> Path:
        return self.base_dir / "trackerx.sqlite3"

    @property
    def backup_dir(self) -> Path:
        path = self.base_dir / "backups"
        path.mkdir(parents=True, exist_ok=True)
        return path


APP_PATHS = AppPaths()
