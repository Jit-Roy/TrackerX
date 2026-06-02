from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    OVERDUE = "overdue"


@dataclass(slots=True)
class Task:
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    due_date: date | None = None
    total_tracked_seconds: int = 0
    id: int | None = None