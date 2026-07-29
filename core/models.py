from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(slots=True)
class Habit:
    title: str
    description: str = ""
    created_date: date | None = None
    id: int | None = None


@dataclass(slots=True)
class WeeklyGoalEntry:
    title: str
    day_of_week: int
    completed: bool = False
    planner_id: int | None = None
    id: int | None = None


@dataclass(slots=True)
class WeeklyPlan:
    week_start_date: date
    title: str = "Weekly Goals"
    entries: list[WeeklyGoalEntry] = field(default_factory=list)
    created_date: date | None = None
    id: int | None = None


@dataclass(slots=True)
class DiaryEntry:
    entry_date: date
    content: str = ""
    id: int | None = None


@dataclass
class ProjectIdea:
    id: int | None
    project_id: int | None
    title: str


@dataclass
class Project:
    id: int | None
    title: str
    description: str = ""
    ideas: list[ProjectIdea] = field(default_factory=list)


@dataclass(slots=True)
class NoteNotebook:
    title: str
    created_date: date | None = None
    id: int | None = None


@dataclass(slots=True)
class NoteSection:
    notebook_id: int
    title: str
    sort_order: int = 0
    id: int | None = None


@dataclass(slots=True)
class Note:
    section_id: int
    title: str = "Untitled"
    content: str = ""
    updated_at: str = ""
    sort_order: int = 0
    id: int | None = None


@dataclass(slots=True)
class NoteNode:
    """Infinite-depth tree node: can be a folder or a leaf note."""
    title: str
    parent_id: int | None = None
    content: str = ""
    sort_order: int = 0
    updated_at: str = ""
    id: int | None = None

