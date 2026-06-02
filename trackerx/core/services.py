from __future__ import annotations

from .database import Database
from .models import TaskStatus, Task, Habit
from .repositories import TaskRepository, HabitRepository


class ProductivityService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.habits = HabitRepository(db)

    def bootstrap(self) -> None:
        pass

    def refresh_overdue_tasks(self) -> None:
        pass

    def get_setting(self, key: str, default: str = "") -> str:
        with self.db.session() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: str | int) -> None:
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )

    def create_task(self, task: Task) -> int:
        return self.tasks.add(task)

    def update_task(self, task_id: int, task: Task) -> None:
        self.tasks.update(task_id, task)

    def delete_task(self, task_id: int) -> None:
        self.tasks.delete(task_id)

    def create_habit(self, habit: Habit) -> int:
        return self.habits.add(habit)

    def update_habit(self, habit_id: int, habit: Habit) -> None:
        self.habits.update(habit_id, habit)

    def delete_habit(self, habit_id: int) -> None:
        self.habits.delete(habit_id)

