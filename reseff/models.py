"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timedelta
import uuid


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Phase:
    """实验阶段模型"""
    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    order: int = 0
    status: str = "pending"  # pending, active, done, blocked
    target_date: Optional[str] = None
    done_at: Optional[str] = None
    task_ids: List[str] = field(default_factory=list)
    note_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Milestone:
    """里程碑模型"""
    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    target_date: Optional[str] = None
    achieved_date: Optional[str] = None
    status: str = "pending"  # pending, active, done, delayed
    task_ids: List[str] = field(default_factory=list)
    phase_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Paper:
    """文献模型"""
    id: str = field(default_factory=_new_id)
    title: str = ""
    authors: str = ""
    year: Optional[int] = None
    venue: str = ""
    url: str = ""
    status: str = "unread"  # unread, reading, read, skipped
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    project: str = ""
    experiment_steps: List[str] = field(default_factory=list)
    note_ids: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)
    read_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Note:
    """笔记模型"""
    id: str = field(default_factory=_new_id)
    content: str = ""
    paper_id: Optional[str] = None
    paper_title: str = ""
    task_id: Optional[str] = None
    task_title: str = ""
    tags: List[str] = field(default_factory=list)
    project: str = ""
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubTask:
    """子任务模型"""
    id: str = field(default_factory=_new_id)
    title: str = ""
    done: bool = False
    done_at: Optional[str] = None
    created_at: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Task:
    """任务模型"""
    id: str = field(default_factory=_new_id)
    title: str = ""
    description: str = ""
    project: str = ""
    priority: str = "medium"  # low, medium, high
    status: str = "todo"  # todo, doing, done, blocked
    due_date: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    subtasks: List[SubTask] = field(default_factory=list)
    experiment_related: bool = False
    paper_id: Optional[str] = None
    note_ids: List[str] = field(default_factory=list)
    phase_id: Optional[str] = None
    milestone_id: Optional[str] = None
    created_at: str = field(default_factory=_now_str)
    updated_at: str = field(default_factory=_now_str)
    done_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.is_done:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d")
            return due.date() < datetime.now().date()
        except ValueError:
            return False

    @property
    def is_due_today(self) -> bool:
        if not self.due_date or self.is_done:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d")
            return due.date() == datetime.now().date()
        except ValueError:
            return False

    @property
    def is_coming_soon(self) -> bool:
        if not self.due_date or self.is_done:
            return False
        if self.is_overdue or self.is_due_today:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d")
            days_left = (due.date() - datetime.now().date()).days
            return 1 <= days_left <= 3
        except ValueError:
            return False

    @property
    def is_long_pending(self) -> bool:
        """超过14天仍未完成的任务"""
        if self.is_done:
            return False
        if self.is_overdue:
            return False
        try:
            created = datetime.strptime(self.created_at.split()[0], "%Y-%m-%d")
            days_passed = (datetime.now().date() - created.date()).days
            return days_passed > 14
        except (ValueError, IndexError):
            return False

    @property
    def is_procrastinated(self) -> bool:
        """被拖延的任务：逾期或超过7天未动"""
        if self.is_done:
            return False
        if self.is_overdue:
            return True
        try:
            created = datetime.strptime(self.created_at.split()[0], "%Y-%m-%d")
            days_passed = (datetime.now().date() - created.date()).days
            return days_passed > 7 and self.status in ["todo", "blocked"]
        except (ValueError, IndexError):
            return False


@dataclass
class WeeklyReport:
    """周报历史记录模型"""
    id: str = field(default_factory=_new_id)
    title: str = ""
    project: str = ""
    start_date: str = ""
    end_date: str = ""
    format: str = "markdown"  # markdown, text, json
    detail_level: str = "full"  # simple, full
    content: str = ""
    metrics: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Project:
    """项目模型"""
    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    archived: bool = False
    milestones: List[Milestone] = field(default_factory=list)
    phases: List[Phase] = field(default_factory=list)
    created_at: str = field(default_factory=_now_str)
    archived_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "archived": self.archived,
            "milestones": [m.to_dict() for m in self.milestones],
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at,
            "archived_at": self.archived_at,
        }


@dataclass
class Database:
    """数据库模型"""
    papers: List[Paper] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    weekly_reports: List[WeeklyReport] = field(default_factory=list)
    initialized_at: str = field(default_factory=_now_str)
    last_updated: str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return {
            "papers": [p.to_dict() for p in self.papers],
            "notes": [n.to_dict() for n in self.notes],
            "tasks": [t.to_dict() for t in self.tasks],
            "projects": [p.to_dict() for p in self.projects],
            "weekly_reports": [r.to_dict() for r in self.weekly_reports],
            "initialized_at": self.initialized_at,
            "last_updated": self.last_updated,
        }
