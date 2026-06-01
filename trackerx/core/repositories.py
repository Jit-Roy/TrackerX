from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .database import Database
from .models import Task, TaskStatus

def _date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None

class TaskRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[Task]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY COALESCE(due_date, '9999-12-31') ASC, id DESC").fetchall()
        return [self._row_to_task(row) for row in rows]

    def get(self, task_id: int) -> Task | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def add(self, task: Task) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, description, status, due_date) VALUES (?, ?, ?, ?)",
                (
                    task.title,
                    task.description,
                    task.status.value,
                    _date_str(task.due_date)
                )
            )
            return cursor.lastrowid

    def update(self, process_id: int, task: Task) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE tasks SET title=?, description=?, status=?, due_date=? WHERE id=?",
                (
                    task.title,
                    task.description,
                    task.status.value,
                    _date_str(task.due_date),
                    process_id
                )
            )

    def delete(self, task_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))

    def mark_completed(self, task_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("UPDATE tasks SET status=? WHERE id=?", (TaskStatus.COMPLETED.value, task_id))

    def mark_skipped(self, task_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("UPDATE tasks SET status=? WHERE id=?", (TaskStatus.SKIPPED.value, task_id))

    def carry_forward(self) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE tasks SET due_date=? WHERE status!=? AND status!=?",
                (_date_str(date.today() + timedelta(days=1)), TaskStatus.COMPLETED.value, TaskStatus.SKIPPED.value)
            )

    def _row_to_task(self, row: Any) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None
        )

