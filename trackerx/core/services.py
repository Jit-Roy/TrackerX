from __future__ import annotations

from datetime import date

from .database import Database
from .models import Habit, Project, ProjectIdea, Task, TaskStatus, WeeklyGoalEntry, WeeklyPlan
from .repositories import TaskRepository, HabitRepository, WeeklyPlannerRepository, ProjectRepository


class ProductivityService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.habits = HabitRepository(db)
        self.planner = WeeklyPlannerRepository(db)
        self.projects = ProjectRepository(db)

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

    def get_weekly_plan(self, week_start_date: date) -> WeeklyPlan | None:
        return self.planner.get_by_week_start(week_start_date)

    def get_or_create_weekly_plan(self, week_start_date: date) -> WeeklyPlan:
        plan = self.get_weekly_plan(week_start_date)
        if plan:
            return plan
        new_plan = WeeklyPlan(
            week_start_date=week_start_date,
            created_date=date.today(),
        )
        new_plan.id = self.planner.add(new_plan)
        return new_plan

    def get_weekly_plan_notes(self, plan_id: int) -> dict[int, str]:
        return self.planner.get_notes(plan_id)

    def save_weekly_plan_note(self, plan_id: int, day_of_week: int, note: str) -> None:
        self.planner.upsert_note(plan_id, day_of_week, note)

    def create_weekly_goal_entry(self, plan_id: int, entry: WeeklyGoalEntry) -> int:
        return self.planner.add_entry(entry, plan_id)

    def update_weekly_goal_entry(self, entry_id: int, entry: WeeklyGoalEntry) -> None:
        self.planner.update_entry(entry_id, entry)

    def delete_weekly_goal_entry(self, entry_id: int) -> None:
        self.planner.delete_entry(entry_id)

    def get_weekly_goal_entry(self, entry_id: int) -> WeeklyGoalEntry | None:
        return self.planner.get_entry(entry_id)

    def list_projects(self) -> list[Project]:
        return self.projects.list()

    def get_project(self, project_id: int) -> Project | None:
        return self.projects.get(project_id)

    def create_project(self, project: Project) -> int:
        return self.projects.add(project)

    def update_project(self, project_id: int, project: Project) -> None:
        self.projects.update(project_id, project)

    def delete_project(self, project_id: int) -> None:
        self.projects.delete(project_id)

    def add_project_idea(self, project_id: int, idea: ProjectIdea) -> int:
        return self.projects.add_idea(project_id, idea)

    def delete_project_idea(self, idea_id: int) -> None:
        self.projects.delete_idea(idea_id)

