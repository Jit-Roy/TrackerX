from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .database import Database
from .models import DiaryEntry, Habit, Project, ProjectIdea, Task, TaskStatus, WeeklyPlan, WeeklyGoalEntry

def _date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _bool_to_int(value: bool) -> int:
    return 1 if value else 0

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
                "INSERT INTO tasks (title, description, status, due_date, tracked_seconds) VALUES (?, ?, ?, ?, ?)",
                (
                    task.title,
                    task.description,
                    task.status.value,
                    _date_str(task.due_date),
                    task.total_tracked_seconds,
                )
            )
            return cursor.lastrowid

    def update(self, process_id: int, task: Task) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE tasks SET title=?, description=?, status=?, due_date=?, tracked_seconds=? WHERE id=?",
                (
                    task.title,
                    task.description,
                    task.status.value,
                    _date_str(task.due_date),
                    task.total_tracked_seconds,
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
            due_date=date.fromisoformat(row["due_date"]) if row["due_date"] else None,
            total_tracked_seconds=int(row["tracked_seconds"] or 0),
        )


class HabitRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[Habit]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM habits ORDER BY created_date DESC").fetchall()
        return [self._row_to_habit(row) for row in rows]

    def get(self, habit_id: int) -> Habit | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()
        return self._row_to_habit(row) if row else None

    def add(self, habit: Habit) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO habits (title, description, created_date) VALUES (?, ?, ?)",
                (
                    habit.title,
                    habit.description,
                    _date_str(habit.created_date or date.today()),
                )
            )
            return cursor.lastrowid

    def update(self, habit_id: int, habit: Habit) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE habits SET title=?, description=? WHERE id=?",
                (habit.title, habit.description, habit_id)
            )

    def delete(self, habit_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))

    def mark_completed(self, habit_id: int, completion_date: date | None = None) -> None:
        """Mark a habit as completed for a specific date."""
        completion_date = completion_date or date.today()
        with self.db.session() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO habit_completions (habit_id, completion_date) VALUES (?, ?)",
                (habit_id, _date_str(completion_date))
            )

    def unmark_completed(self, habit_id: int, completion_date: date | None = None) -> None:
        """Unmark a habit as completed for a specific date."""
        completion_date = completion_date or date.today()
        with self.db.session() as conn:
            conn.execute(
                "DELETE FROM habit_completions WHERE habit_id=? AND completion_date=?",
                (habit_id, _date_str(completion_date))
            )

    def get_completions(self, habit_id: int, start_date: date, end_date: date) -> set[date]:
        """Get all completion dates for a habit in a date range."""
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT completion_date FROM habit_completions WHERE habit_id=? AND completion_date BETWEEN ? AND ? ORDER BY completion_date",
                (habit_id, _date_str(start_date), _date_str(end_date))
            ).fetchall()
        return {date.fromisoformat(row["completion_date"]) for row in rows}

    def _row_to_habit(self, row: Any) -> Habit:
        return Habit(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            created_date=date.fromisoformat(row["created_date"]) if row["created_date"] else None,
        )


class WeeklyPlannerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_by_week_start(self, week_start_date: date) -> WeeklyPlan | None:
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_plans WHERE week_start_date = ?",
                (_date_str(week_start_date),),
            ).fetchone()
        if not row:
            return None
        plan = self._row_to_plan(row)
        plan.entries = self.list_entries(plan.id)
        return plan

    def get_by_id(self, plan_id: int) -> WeeklyPlan | None:
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_plans WHERE id = ?",
                (plan_id,),
            ).fetchone()
        if not row:
            return None
        plan = self._row_to_plan(row)
        plan.entries = self.list_entries(plan.id)
        return plan

    def get_notes(self, plan_id: int) -> dict[int, str]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT day_of_week, note FROM weekly_plan_notes WHERE plan_id = ?",
                (plan_id,),
            ).fetchall()
        return {int(row["day_of_week"]): row["note"] for row in rows}

    def get_note(self, plan_id: int, day_of_week: int) -> str | None:
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT note FROM weekly_plan_notes WHERE plan_id = ? AND day_of_week = ?",
                (plan_id, day_of_week),
            ).fetchone()
        return row["note"] if row else None

    def upsert_note(self, plan_id: int, day_of_week: int, note: str) -> None:
        with self.db.session() as conn:
            if note.strip() == "":
                conn.execute(
                    "DELETE FROM weekly_plan_notes WHERE plan_id = ? AND day_of_week = ?",
                    (plan_id, day_of_week),
                )
            else:
                conn.execute(
                    "INSERT INTO weekly_plan_notes (plan_id, day_of_week, note) VALUES (?, ?, ?) "
                    "ON CONFLICT(plan_id, day_of_week) DO UPDATE SET note = excluded.note",
                    (plan_id, day_of_week, note),
                )

    def list(self) -> list[WeeklyPlan]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM weekly_plans ORDER BY week_start_date DESC").fetchall()
        plans = [self._row_to_plan(row) for row in rows]
        for plan in plans:
            if plan.id is not None:
                plan.entries = self.list_entries(plan.id)
        return plans

    def add(self, plan: WeeklyPlan) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO weekly_plans (title, week_start_date, created_date) VALUES (?, ?, ?)",
                (
                    plan.title,
                    _date_str(plan.week_start_date),
                    _date_str(plan.created_date or date.today()),
                ),
            )
            plan_id = cursor.lastrowid
            for entry in plan.entries:
                self.add_entry(entry, plan_id, conn)
            return plan_id

    def update(self, plan_id: int, plan: WeeklyPlan) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE weekly_plans SET title=?, week_start_date=? WHERE id=?",
                (
                    plan.title,
                    _date_str(plan.week_start_date),
                    plan_id,
                ),
            )

    def delete(self, plan_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM weekly_plans WHERE id=?", (plan_id,))

    def list_entries(self, plan_id: int) -> list[WeeklyGoalEntry]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT * FROM weekly_plan_entries WHERE plan_id=? ORDER BY day_of_week, id",
                (plan_id,),
            ).fetchall()
        return [self._row_to_goal_entry(row) for row in rows]

    def get_entry(self, entry_id: int) -> WeeklyGoalEntry | None:
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_plan_entries WHERE id=?",
                (entry_id,),
            ).fetchone()
        return self._row_to_goal_entry(row) if row else None

    def add_entry(self, entry: WeeklyGoalEntry, plan_id: int, conn=None) -> int:
        close_conn = False
        if conn is None:
            conn = self.db.connect()
            close_conn = True
        cursor = conn.execute(
            "INSERT INTO weekly_plan_entries (plan_id, day_of_week, title, completed) VALUES (?, ?, ?, ?)",
            (
                plan_id,
                entry.day_of_week,
                entry.title,
                _bool_to_int(entry.completed),
            ),
        )
        if close_conn:
            conn.commit()
            conn.close()
        return cursor.lastrowid

    def update_entry(self, entry_id: int, entry: WeeklyGoalEntry) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE weekly_plan_entries SET title=?, day_of_week=?, completed=? WHERE id=?",
                (
                    entry.title,
                    entry.day_of_week,
                    _bool_to_int(entry.completed),
                    entry_id,
                ),
            )

    def delete_entry(self, entry_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM weekly_plan_entries WHERE id=?", (entry_id,))

    def _row_to_plan(self, row: Any) -> WeeklyPlan:
        return WeeklyPlan(
            id=row["id"],
            title=row["title"],
            week_start_date=date.fromisoformat(row["week_start_date"]),
            created_date=date.fromisoformat(row["created_date"]),
        )


    def _row_to_goal_entry(self, row: Any) -> WeeklyGoalEntry:
        return WeeklyGoalEntry(
            id=row["id"],
            planner_id=row["plan_id"],
            title=row["title"],
            day_of_week=int(row["day_of_week"]),
            completed=bool(row["completed"]),
        )


class DiaryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[DiaryEntry]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM diary_entries ORDER BY entry_date DESC").fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_by_date(self, entry_date: date) -> DiaryEntry | None:
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM diary_entries WHERE entry_date = ?",
                (_date_str(entry_date),),
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def add(self, entry: DiaryEntry) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO diary_entries (entry_date, content) VALUES (?, ?)",
                (_date_str(entry.entry_date), entry.content),
            )
            return cursor.lastrowid

    def update(self, entry_id: int, entry: DiaryEntry) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE diary_entries SET content = ? WHERE id = ?",
                (entry.content, entry_id),
            )

    def delete(self, entry_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))

    def _row_to_entry(self, row: Any) -> DiaryEntry:
        return DiaryEntry(
            id=row["id"],
            entry_date=date.fromisoformat(row["entry_date"]),
            content=row["content"],
        )


class ProjectRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[Project]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
        projects = [self._row_to_project(row) for row in rows]
        for project in projects:
            if project.id is not None:
                project.ideas = self.list_ideas(project.id)
        return projects

    def get(self, project_id: int) -> Project | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            return None
        project = self._row_to_project(row)
        project.ideas = self.list_ideas(project_id)
        return project

    def add(self, project: Project) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (title, description) VALUES (?, ?)",
                (project.title, project.description),
            )
            return cursor.lastrowid

    def update(self, project_id: int, project: Project) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE projects SET title=?, description=? WHERE id=?",
                (project.title, project.description, project_id),
            )

    def delete(self, project_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def list_ideas(self, project_id: int) -> list[ProjectIdea]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT * FROM project_ideas WHERE project_id=? ORDER BY id DESC",
                (project_id,),
            ).fetchall()
        return [self._row_to_project_idea(row) for row in rows]

    def add_idea(self, project_id: int, idea: ProjectIdea) -> int:
        with self.db.session() as conn:
            cursor = conn.execute(
                "INSERT INTO project_ideas (project_id, title) VALUES (?, ?)",
                (project_id, idea.title),
            )
            return cursor.lastrowid

    def delete_idea(self, idea_id: int) -> None:
        with self.db.session() as conn:
            conn.execute("DELETE FROM project_ideas WHERE id=?", (idea_id,))

    def _row_to_project(self, row: Any) -> Project:
        return Project(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            ideas=[],
        )

    def _row_to_project_idea(self, row: Any) -> ProjectIdea:
        return ProjectIdea(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
        )

