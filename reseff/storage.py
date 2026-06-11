"""数据存储模块"""
import json
from pathlib import Path
from typing import List, Optional, TypeVar, Callable, Dict, Tuple
from datetime import datetime, timedelta

from .models import (
    Database, Paper, Note, Task, Project, SubTask,
    Phase, Milestone, WeeklyReport, _now_str,
)

T = TypeVar("T")

DEFAULT_DIR = ".reseff"
DB_FILE = "reseff_data.json"


def get_storage_path() -> Path:
    """获取存储目录路径"""
    home = Path.home()
    return home / DEFAULT_DIR


def get_db_path() -> Path:
    """获取数据库文件路径"""
    return get_storage_path() / DB_FILE


def is_initialized() -> bool:
    """检查是否已初始化"""
    return get_db_path().exists()


def init_storage(force: bool = False) -> bool:
    """初始化存储目录"""
    storage_dir = get_storage_path()
    db_path = get_db_path()

    if db_path.exists() and not force:
        return False

    storage_dir.mkdir(parents=True, exist_ok=True)
    db = Database()
    save_db(db)
    return True


def save_db(db: Database) -> None:
    """保存数据库到文件"""
    db.last_updated = _now_str()
    db_path = get_db_path()
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db.to_dict(), f, ensure_ascii=False, indent=2)


def _safe_migrate_paper(p: dict) -> Paper:
    """兼容旧版数据，迁移 Paper"""
    if "note_ids" not in p:
        p["note_ids"] = p.get("notes", [])
    if "task_ids" not in p:
        p["task_ids"] = []
    p.pop("notes", None)
    return Paper(**p)


def _safe_migrate_note(n: dict) -> Note:
    """兼容旧版数据，迁移 Note"""
    if "task_id" not in n:
        n["task_id"] = None
    if "task_title" not in n:
        n["task_title"] = ""
    return Note(**n)


def _safe_migrate_task(t: dict) -> Task:
    """兼容旧版数据，迁移 Task"""
    subtasks = [SubTask(**st) for st in t.get("subtasks", [])]
    t["subtasks"] = subtasks
    if "note_ids" not in t:
        t["note_ids"] = []
    if "phase_id" not in t:
        t["phase_id"] = None
    if "milestone_id" not in t:
        t["milestone_id"] = None
    return Task(**t)


def _safe_migrate_project(p: dict) -> Project:
    """兼容旧版数据，迁移 Project"""
    if "milestones" not in p:
        p["milestones"] = []
    if "phases" not in p:
        p["phases"] = []

    milestones = [Milestone(**m) for m in p.get("milestones", [])]
    phases = [Phase(**ph) for ph in p.get("phases", [])]
    p["milestones"] = milestones
    p["phases"] = phases
    return Project(**p)


def _safe_migrate_weekly_report(r: dict) -> WeeklyReport:
    """兼容旧版数据，迁移 WeeklyReport"""
    return WeeklyReport(**r)


def load_db() -> Database:
    """从文件加载数据库"""
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在，请先运行 init 命令: {db_path}")

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = [_safe_migrate_paper(p) for p in data.get("papers", [])]
    notes = [_safe_migrate_note(n) for n in data.get("notes", [])]
    tasks = [_safe_migrate_task(t) for t in data.get("tasks", [])]
    projects = [_safe_migrate_project(p) for p in data.get("projects", [])]
    weekly_reports = [_safe_migrate_weekly_report(r) for r in data.get("weekly_reports", [])]

    return Database(
        papers=papers,
        notes=notes,
        tasks=tasks,
        projects=projects,
        weekly_reports=weekly_reports,
        initialized_at=data.get("initialized_at", _now_str()),
        last_updated=data.get("last_updated", _now_str()),
    )


def _find_by_id(items: List[T], id: str) -> Optional[T]:
    """通过ID查找项"""
    for item in items:
        if item.id == id:
            return item
    return None


def ensure_project(db: Database, project_name: str) -> Project:
    """确保项目存在，不存在则自动创建"""
    if not project_name:
        return None
    project = get_project(db, project_name)
    if not project:
        project = Project(name=project_name)
        add_project(db, project)
    return project


# ==================== Paper 相关 ====================

def add_paper(db: Database, paper: Paper) -> Paper:
    """添加文献"""
    db.papers.append(paper)
    if paper.project:
        ensure_project(db, paper.project)
    save_db(db)
    return paper


def get_paper(db: Database, id: str) -> Optional[Paper]:
    """获取文献"""
    return _find_by_id(db.papers, id)


def update_paper(db: Database, id: str, **kwargs) -> Optional[Paper]:
    """更新文献"""
    paper = _find_by_id(db.papers, id)
    if paper:
        for key, value in kwargs.items():
            if hasattr(paper, key) and value is not None:
                setattr(paper, key, value)
        if "project" in kwargs and kwargs["project"]:
            ensure_project(db, kwargs["project"])
        paper.updated_at = _now_str()
        save_db(db)
    return paper


def delete_paper(db: Database, id: str) -> bool:
    """删除文献"""
    paper = _find_by_id(db.papers, id)
    if paper:
        for note in db.notes:
            if note.paper_id == id:
                note.paper_id = None
                note.paper_title = ""
        for task in db.tasks:
            if task.paper_id == id:
                task.paper_id = None
        db.papers.remove(paper)
        save_db(db)
        return True
    return False


def list_papers(db: Database, project: Optional[str] = None, status: Optional[str] = None) -> List[Paper]:
    """列出文献"""
    papers = db.papers
    if project:
        papers = [p for p in papers if p.project == project]
    if status:
        papers = [p for p in papers if p.status == status]
    return papers


def get_paper_notes(db: Database, paper_id: str) -> List[Note]:
    """获取文献关联的笔记"""
    return [n for n in db.notes if n.paper_id == paper_id]


def get_paper_tasks(db: Database, paper_id: str) -> List[Task]:
    """获取文献关联的任务"""
    return [t for t in db.tasks if t.paper_id == paper_id]


# ==================== Note 相关 ====================

def add_note(db: Database, note: Note) -> Note:
    """添加笔记，同时维护双向关联"""
    db.notes.append(note)
    if note.paper_id:
        paper = get_paper(db, note.paper_id)
        if paper and note.id not in paper.note_ids:
            paper.note_ids.append(note.id)
            paper.updated_at = _now_str()
    if note.task_id:
        task = get_task(db, note.task_id)
        if task and note.id not in task.note_ids:
            task.note_ids.append(note.id)
            task.updated_at = _now_str()
    if note.project:
        ensure_project(db, note.project)
    save_db(db)
    return note


def get_note(db: Database, id: str) -> Optional[Note]:
    """获取笔记"""
    return _find_by_id(db.notes, id)


def update_note(db: Database, id: str, **kwargs) -> Optional[Note]:
    """更新笔记"""
    note = _find_by_id(db.notes, id)
    if note:
        for key, value in kwargs.items():
            if hasattr(note, key) and value is not None:
                setattr(note, key, value)
        if "project" in kwargs and kwargs["project"]:
            ensure_project(db, kwargs["project"])
        note.updated_at = _now_str()
        save_db(db)
    return note


def delete_note(db: Database, id: str) -> bool:
    """删除笔记"""
    note = _find_by_id(db.notes, id)
    if note:
        if note.paper_id:
            paper = get_paper(db, note.paper_id)
            if paper and id in paper.note_ids:
                paper.note_ids.remove(id)
        if note.task_id:
            task = get_task(db, note.task_id)
            if task and id in task.note_ids:
                task.note_ids.remove(id)
        db.notes.remove(note)
        save_db(db)
        return True
    return False


def list_notes(db: Database, paper_id: Optional[str] = None, task_id: Optional[str] = None,
               project: Optional[str] = None) -> List[Note]:
    """列出笔记"""
    notes = db.notes
    if paper_id:
        notes = [n for n in notes if n.paper_id == paper_id]
    if task_id:
        notes = [n for n in notes if n.task_id == task_id]
    if project:
        notes = [n for n in notes if n.project == project]
    return notes


def get_task_notes(db: Database, task_id: str) -> List[Note]:
    """获取任务关联的笔记"""
    return [n for n in db.notes if n.task_id == task_id]


# ==================== Task 相关 ====================

def add_task(db: Database, task: Task) -> Task:
    """添加任务，同时维护双向关联"""
    db.tasks.append(task)
    if task.paper_id:
        paper = get_paper(db, task.paper_id)
        if paper and task.id not in paper.task_ids:
            paper.task_ids.append(task.id)
            paper.updated_at = _now_str()
    if task.project:
        ensure_project(db, task.project)
    save_db(db)
    return task


def get_task(db: Database, id: str) -> Optional[Task]:
    """获取任务"""
    return _find_by_id(db.tasks, id)


def update_task(db: Database, id: str, **kwargs) -> Optional[Task]:
    """更新任务"""
    task = _find_by_id(db.tasks, id)
    if task:
        old_paper_id = task.paper_id
        for key, value in kwargs.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        if "paper_id" in kwargs and kwargs["paper_id"] != old_paper_id:
            if old_paper_id:
                old_paper = get_paper(db, old_paper_id)
                if old_paper and id in old_paper.task_ids:
                    old_paper.task_ids.remove(id)
            if kwargs["paper_id"]:
                new_paper = get_paper(db, kwargs["paper_id"])
                if new_paper and id not in new_paper.task_ids:
                    new_paper.task_ids.append(id)
        if "project" in kwargs and kwargs["project"]:
            ensure_project(db, kwargs["project"])
        task.updated_at = _now_str()
        if task.status == "done" and not task.done_at:
            task.done_at = _now_str()
        save_db(db)
    return task


def delete_task(db: Database, id: str) -> bool:
    """删除任务"""
    task = _find_by_id(db.tasks, id)
    if task:
        if task.paper_id:
            paper = get_paper(db, task.paper_id)
            if paper and id in paper.task_ids:
                paper.task_ids.remove(id)
        for note in db.notes:
            if note.task_id == id:
                note.task_id = None
                note.task_title = ""
        db.tasks.remove(task)
        save_db(db)
        return True
    return False


def list_tasks(
    db: Database,
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    experiment_only: bool = False,
) -> List[Task]:
    """列出任务"""
    tasks = db.tasks
    if project:
        tasks = [t for t in tasks if t.project == project]
    if status:
        tasks = [t for t in tasks if t.status == status]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if experiment_only:
        tasks = [t for t in tasks if t.experiment_related]
    return tasks


def get_task_paper(db: Database, task_id: str) -> Optional[Paper]:
    """获取任务关联的文献"""
    task = get_task(db, task_id)
    if task and task.paper_id:
        return get_paper(db, task.paper_id)
    return None


def get_today_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取今日到期的任务"""
    tasks = [t for t in db.tasks if t.is_due_today]
    if project:
        tasks = [t for t in tasks if t.project == project]
    return tasks


def get_coming_soon_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取即将到期的任务（1-3天内）"""
    tasks = [t for t in db.tasks if t.is_coming_soon]
    if project:
        tasks = [t for t in tasks if t.project == project]
    return tasks


def get_overdue_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取逾期任务"""
    tasks = [t for t in db.tasks if t.is_overdue]
    if project:
        tasks = [t for t in tasks if t.project == project]
    return tasks


def get_long_pending_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取长期未处理的任务（超过14天）"""
    tasks = [t for t in db.tasks if t.is_long_pending]
    if project:
        tasks = [t for t in tasks if t.project == project]
    return tasks


def get_procrastinated_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取拖延任务"""
    tasks = [t for t in db.tasks if t.is_procrastinated]
    if project:
        tasks = [t for t in tasks if t.project == project]
    return tasks


def get_reminder_tasks(db: Database, project: Optional[str] = None) -> Dict[str, List[Task]]:
    """获取所有需要提醒的任务，按类型分组

    覆盖所有未完成任务：
    - overdue: 逾期
    - today: 今日到期
    - coming_soon: 即将到期（7天内）
    - long_term: 远期计划（7天以上）
    - no_deadline: 无截止日期
    """
    all_undone = [t for t in db.tasks if not t.is_done]
    if project:
        all_undone = [t for t in all_undone if t.project == project]

    today = []
    coming_soon = []
    overdue = []
    long_term = []
    no_deadline = []

    now = datetime.now().date()

    for t in all_undone:
        if not t.due_date:
            no_deadline.append(t)
            continue

        try:
            due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
            days_left = (due - now).days

            if days_left < 0:
                overdue.append(t)
            elif days_left == 0:
                today.append(t)
            elif 1 <= days_left <= 7:
                coming_soon.append(t)
            else:
                long_term.append(t)
        except ValueError:
            no_deadline.append(t)

    def _sort_by_due(tasks):
        return sorted(tasks, key=lambda x: x.due_date or "9999-99-99")

    return {
        "overdue": _sort_by_due(overdue),
        "today": _sort_by_due(today),
        "coming_soon": _sort_by_due(coming_soon),
        "long_term": _sort_by_due(long_term),
        "no_deadline": sorted(no_deadline, key=lambda x: x.created_at, reverse=True),
    }


# ==================== 时间范围查询 ====================

def _parse_date(s: str) -> Optional[datetime]:
    """尝试解析日期字符串"""
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def get_tasks_in_range(
    db: Database,
    start_date: str,
    end_date: str,
    project: Optional[str] = None,
) -> Dict[str, List[Task]]:
    """按时间范围获取任务

    返回: {
        'created': 创建时间在范围内的任务,
        'completed': 完成时间在范围内的任务,
        'overdue_in_range': 在范围内到期且逾期的任务,
        'all_active': 范围内所有未完成任务
    }
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end:
        return {"created": [], "completed": [], "overdue_in_range": [], "all_active": []}

    start_date_only = start.date()
    end_date_only = end.date()

    created, completed, overdue_in_range, all_active = [], [], [], []

    for t in db.tasks:
        if project and t.project != project:
            continue

        c = _parse_date(t.created_at)
        if c and start_date_only <= c.date() <= end_date_only:
            created.append(t)

        if t.done_at:
            d = _parse_date(t.done_at)
            if d and start_date_only <= d.date() <= end_date_only:
                completed.append(t)

        if t.due_date and not t.is_done:
            try:
                due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
                if start_date_only <= due <= end_date_only and t.is_overdue:
                    overdue_in_range.append(t)
            except ValueError:
                pass

        if not t.is_done:
            if c and c.date() <= end_date_only:
                all_active.append(t)

    return {
        "created": created,
        "completed": completed,
        "overdue_in_range": overdue_in_range,
        "all_active": all_active,
    }


def get_papers_in_range(
    db: Database,
    start_date: str,
    end_date: str,
    project: Optional[str] = None,
) -> Dict[str, List[Paper]]:
    """按时间范围获取文献"""
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end:
        return {"created": [], "read": []}

    start_date_only = start.date()
    end_date_only = end.date()

    created, read = [], []

    for p in db.papers:
        if project and p.project != project:
            continue

        c = _parse_date(p.created_at)
        if c and start_date_only <= c.date() <= end_date_only:
            created.append(p)

        if p.read_at:
            r = _parse_date(p.read_at)
            if r and start_date_only <= r.date() <= end_date_only:
                read.append(p)

    return {"created": created, "read": read}


def get_experiment_progress_in_range(
    db: Database,
    start_date: str,
    end_date: str,
    project: Optional[str] = None,
) -> Dict:
    """获取时间范围内的实验进展"""
    task_data = get_tasks_in_range(db, start_date, end_date, project)
    exp_tasks = [t for t in task_data["all_active"] + task_data["completed"] if t.experiment_related]
    exp_done = [t for t in exp_tasks if t.is_done]
    exp_active = [t for t in exp_tasks if not t.is_done]

    return {
        "total_experiments": len(exp_tasks),
        "completed_experiments": len(exp_done),
        "active_experiments": len(exp_active),
        "completed_tasks": exp_done,
        "active_tasks": exp_active,
    }


def get_this_week_tasks(db: Database, project: Optional[str] = None) -> List[Task]:
    """获取本周任务"""
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    end_of_week = (now + timedelta(days=6 - now.weekday())).strftime("%Y-%m-%d")
    data = get_tasks_in_range(db, start_of_week, end_of_week, project)
    return list(set(data["created"] + data["completed"] + data["all_active"]))


def get_this_week_completion(db: Database, project: Optional[str] = None) -> dict:
    """获取本周完成率"""
    tasks = get_this_week_tasks(db, project)
    created = [t for t in tasks if t.created_at]
    completed = [t for t in tasks if t.is_done and t.done_at]

    return {
        "created": len(created),
        "completed": len(completed),
        "total_active": len([t for t in tasks if not t.is_done]),
    }


def add_subtask(db: Database, task_id: str, subtask: SubTask) -> Optional[SubTask]:
    """添加子任务"""
    task = _find_by_id(db.tasks, task_id)
    if task:
        task.subtasks.append(subtask)
        task.updated_at = _now_str()
        save_db(db)
        return subtask
    return None


def toggle_subtask(db: Database, task_id: str, subtask_id: str) -> Optional[SubTask]:
    """切换子任务完成状态"""
    task = _find_by_id(db.tasks, task_id)
    if task:
        for st in task.subtasks:
            if st.id == subtask_id:
                st.done = not st.done
                st.done_at = _now_str() if st.done else None
                task.updated_at = _now_str()
                all_done = all(s.done for s in task.subtasks) and len(task.subtasks) > 0
                if all_done and task.status != "done":
                    task.status = "done"
                    task.done_at = _now_str()
                save_db(db)
                return st
    return None


# ==================== Project / Phase / Milestone ====================

def add_project(db: Database, project: Project) -> Project:
    """添加项目"""
    db.projects.append(project)
    save_db(db)
    return project


def get_project(db: Database, name: str) -> Optional[Project]:
    """获取项目"""
    for p in db.projects:
        if p.name == name:
            return p
    return None


def update_project(db: Database, name: str, **kwargs) -> Optional[Project]:
    """更新项目"""
    project = get_project(db, name)
    if project:
        for key, value in kwargs.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        save_db(db)
    return project


def archive_project(db: Database, name: str) -> Optional[Project]:
    """归档项目"""
    project = get_project(db, name)
    if project:
        project.archived = True
        project.archived_at = _now_str()
        save_db(db)
    return project


def list_projects(db: Database, include_archived: bool = False) -> List[Project]:
    """列出项目"""
    if include_archived:
        return db.projects
    return [p for p in db.projects if not p.archived]


def add_phase(db: Database, project_name: str, phase: Phase) -> Optional[Phase]:
    """为项目添加实验阶段"""
    project = get_project(db, project_name)
    if not project:
        project = ensure_project(db, project_name)
    if phase.order == 0:
        phase.order = len(project.phases) + 1
    project.phases.append(phase)
    project.updated_at = _now_str() if hasattr(project, 'updated_at') else _now_str()
    save_db(db)
    return phase


def get_phase(db: Database, project_name: str, phase_id: str) -> Optional[Phase]:
    """获取项目阶段"""
    project = get_project(db, project_name)
    if not project:
        return None
    return _find_by_id(project.phases, phase_id)


def update_phase(db: Database, project_name: str, phase_id: str, **kwargs) -> Optional[Phase]:
    """更新项目阶段"""
    phase = get_phase(db, project_name, phase_id)
    if phase:
        for key, value in kwargs.items():
            if hasattr(phase, key) and value is not None:
                setattr(phase, key, value)
        if phase.status == "done" and not phase.done_at:
            phase.done_at = _now_str()
        phase.updated_at = _now_str()
        save_db(db)
    return phase


def delete_phase(db: Database, project_name: str, phase_id: str) -> bool:
    """删除项目阶段"""
    project = get_project(db, project_name)
    if not project:
        return False
    phase = _find_by_id(project.phases, phase_id)
    if phase:
        for t in db.tasks:
            if t.phase_id == phase_id:
                t.phase_id = None
        project.phases.remove(phase)
        save_db(db)
        return True
    return False


def get_phase_tasks(db: Database, project_name: str, phase_id: str) -> List[Task]:
    """获取阶段关联的任务"""
    return [t for t in db.tasks if t.phase_id == phase_id]


def get_current_phase(db: Database, project_name: str) -> Optional[Phase]:
    """获取项目当前进行中的阶段"""
    project = get_project(db, project_name)
    if not project or not project.phases:
        return None
    active = [p for p in project.phases if p.status == "active"]
    if active:
        return sorted(active, key=lambda x: x.order)[0]
    pending = [p for p in project.phases if p.status == "pending"]
    if pending:
        return sorted(pending, key=lambda x: x.order)[0]
    return sorted(project.phases, key=lambda x: x.order)[-1]


def get_blocked_tasks_in_phase(db: Database, project_name: str, phase_id: str) -> List[Task]:
    """获取阶段中被阻塞的任务"""
    tasks = get_phase_tasks(db, project_name, phase_id)
    return [t for t in tasks if t.status == "blocked"]


def add_milestone(db: Database, project_name: str, milestone: Milestone) -> Optional[Milestone]:
    """为项目添加里程碑"""
    project = get_project(db, project_name)
    if not project:
        project = ensure_project(db, project_name)
    project.milestones.append(milestone)
    save_db(db)
    return milestone


def get_milestone(db: Database, project_name: str, milestone_id: str) -> Optional[Milestone]:
    """获取里程碑"""
    project = get_project(db, project_name)
    if not project:
        return None
    return _find_by_id(project.milestones, milestone_id)


def update_milestone(db: Database, project_name: str, milestone_id: str, **kwargs) -> Optional[Milestone]:
    """更新里程碑"""
    milestone = get_milestone(db, project_name, milestone_id)
    if milestone:
        for key, value in kwargs.items():
            if hasattr(milestone, key) and value is not None:
                setattr(milestone, key, value)
        if milestone.status == "done" and not milestone.achieved_date:
            milestone.achieved_date = _now_str()
        milestone.updated_at = _now_str()
        save_db(db)
    return milestone


def delete_milestone(db: Database, project_name: str, milestone_id: str) -> bool:
    """删除里程碑"""
    project = get_project(db, project_name)
    if not project:
        return False
    milestone = _find_by_id(project.milestones, milestone_id)
    if milestone:
        for t in db.tasks:
            if t.milestone_id == milestone_id:
                t.milestone_id = None
        project.milestones.remove(milestone)
        save_db(db)
        return True
    return False


def get_milestone_tasks(db: Database, project_name: str, milestone_id: str) -> List[Task]:
    """获取里程碑关联的任务"""
    return [t for t in db.tasks if t.milestone_id == milestone_id]


def get_project_progress(db: Database, project_name: str) -> Dict:
    """获取项目整体进度"""
    tasks = list_tasks(db, project=project_name)
    papers = list_papers(db, project=project_name)
    project = get_project(db, project_name)

    total_tasks = len(tasks)
    done_tasks = len([t for t in tasks if t.is_done])
    exp_tasks = [t for t in tasks if t.experiment_related]
    blocked_tasks = [t for t in tasks if t.status == "blocked"]

    total_papers = len(papers)
    read_papers = len([p for p in papers if p.status == "read"])

    phases = project.phases if project else []
    done_phases = [p for p in phases if p.status == "done"]
    active_phase = get_current_phase(db, project_name)

    milestones = project.milestones if project else []
    done_milestones = [m for m in milestones if m.status == "done"]

    return {
        "task_completion": (done_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "active_tasks": len([t for t in tasks if t.status == "doing"]),
        "blocked_tasks": blocked_tasks,
        "paper_progress": (read_papers / total_papers * 100) if total_papers > 0 else 0,
        "total_papers": total_papers,
        "read_papers": read_papers,
        "total_phases": len(phases),
        "done_phases": len(done_phases),
        "active_phase": active_phase,
        "total_milestones": len(milestones),
        "done_milestones": len(done_milestones),
        "experiment_count": len(exp_tasks),
        "experiment_done": len([t for t in exp_tasks if t.is_done]),
    }


# ==================== 搜索 ====================

def search_notes(db: Database, keyword: str) -> List[Note]:
    """搜索笔记"""
    kw = keyword.lower()
    return [n for n in db.notes if kw in n.content.lower() or any(kw in t.lower() for t in n.tags)]


def search_papers(db: Database, keyword: str) -> List[Paper]:
    """搜索文献"""
    kw = keyword.lower()
    return [
        p for p in db.papers
        if kw in p.title.lower()
        or kw in p.authors.lower()
        or kw in p.summary.lower()
        or any(kw in t.lower() for t in p.tags)
    ]


def search_tasks(db: Database, keyword: str) -> List[Task]:
    """搜索任务"""
    kw = keyword.lower()
    return [
        t for t in db.tasks
        if kw in t.title.lower()
        or kw in t.description.lower()
        or any(kw in tag.lower() for tag in t.tags)
    ]


def search_all(db: Database, keyword: str, project: Optional[str] = None) -> Dict[str, list]:
    """综合搜索：同时搜索文献、笔记、任务

    返回: {'papers': [...], 'notes': [...], 'tasks': [...]}
    """
    papers = search_papers(db, keyword)
    notes = search_notes(db, keyword)
    tasks = search_tasks(db, keyword)

    if project:
        papers = [p for p in papers if p.project == project]
        notes = [n for n in notes if n.project == project]
        tasks = [t for t in tasks if t.project == project]

    return {"papers": papers, "notes": notes, "tasks": tasks}


# ==================== 统计 ====================

def get_completion_rate(db: Database, project: Optional[str] = None) -> dict:
    """获取完成率统计"""
    tasks = list_tasks(db, project=project) if project else db.tasks
    total = len(tasks)
    done = len([t for t in tasks if t.status == "done"])
    doing = len([t for t in tasks if t.status == "doing"])
    todo = len([t for t in tasks if t.status == "todo"])
    blocked = len([t for t in tasks if t.status == "blocked"])
    overdue = len([t for t in tasks if t.is_overdue])
    procrastinated = len([t for t in tasks if t.is_procrastinated])
    long_pending = len([t for t in tasks if t.is_long_pending])
    today = len([t for t in tasks if t.is_due_today])
    coming_soon = len([t for t in tasks if t.is_coming_soon])

    return {
        "total": total,
        "done": done,
        "doing": doing,
        "todo": todo,
        "blocked": blocked,
        "overdue": overdue,
        "procrastinated": procrastinated,
        "long_pending": long_pending,
        "today": today,
        "coming_soon": coming_soon,
        "rate": (done / total * 100) if total > 0 else 0,
    }


# ==================== WeeklyReport 相关 ====================

def add_weekly_report(db: Database, report: WeeklyReport) -> WeeklyReport:
    """添加周报历史记录"""
    db.weekly_reports.append(report)
    if report.project:
        ensure_project(db, report.project)
    save_db(db)
    return report


def get_weekly_report(db: Database, id: str) -> Optional[WeeklyReport]:
    """获取周报历史记录"""
    return _find_by_id(db.weekly_reports, id)


def list_weekly_reports(db: Database, project: Optional[str] = None) -> List[WeeklyReport]:
    """列出周报历史记录"""
    reports = db.weekly_reports
    if project:
        reports = [r for r in reports if r.project == project]
    return reports


def delete_weekly_report(db: Database, id: str) -> bool:
    """删除周报历史记录"""
    report = _find_by_id(db.weekly_reports, id)
    if report:
        db.weekly_reports.remove(report)
        save_db(db)
        return True
    return False


# ==================== Phase 任务统计 ====================

def get_phase_task_count(db: Database, project_name: str, phase_id: str) -> Dict[str, int]:
    """获取阶段任务统计（直接查 tasks 表，确保数字一致）"""
    tasks = get_phase_tasks(db, project_name, phase_id)
    total = len(tasks)
    done = len([t for t in tasks if t.is_done])
    blocked = len([t for t in tasks if t.status == "blocked"])
    return {"total": total, "done": done, "blocked": blocked}


# ==================== Paper 去重统计 ====================

def get_papers_in_range_dedup(
    db: Database,
    start_date: str,
    end_date: str,
    project: Optional[str] = None,
) -> Dict:
    """按时间范围获取文献（去重）

    返回: {
        'total_unique': 去重后总文献数,
        'read_unique': 时间范围内读完的文献数,
        'created': 创建时间在范围内的文献列表,
        'read': 阅读时间在范围内的文献列表,
        'all_papers': 去重后的所有文献列表
    }
    """
    data = get_papers_in_range(db, start_date, end_date, project)
    created = data["created"]
    read = data["read"]

    all_paper_ids = set()
    all_papers = []

    for p in created + read:
        if p.id not in all_paper_ids:
            all_paper_ids.add(p.id)
            all_papers.append(p)

    total_unique = len(all_papers)
    read_unique = len(read)

    return {
        "total_unique": total_unique,
        "read_unique": read_unique,
        "created": created,
        "read": read,
        "all_papers": all_papers,
    }


# ==================== 实验长期未动检测 ====================

def get_stagnant_experiments(
    db: Database,
    project: Optional[str] = None,
    days: int = 7,
) -> List[Task]:
    """获取超过指定天数未更新的实验相关任务"""
    now = datetime.now()
    threshold = now - timedelta(days=days)

    tasks = list_tasks(db, project=project, experiment_only=True)
    stagnant = []

    for t in tasks:
        if t.is_done:
            continue
        updated = _parse_date(t.updated_at)
        if updated and updated < threshold:
            stagnant.append(t)

    return stagnant


# ==================== 远期任务查询 ====================

def get_long_term_tasks(
    db: Database,
    project: Optional[str] = None,
    days_from_now: int = 14,
) -> List[Task]:
    """获取截止日期在指定天数之后的未完成任务（远期计划）"""
    now = datetime.now()
    threshold_date = (now + timedelta(days=days_from_now)).date()

    tasks = list_tasks(db, project=project)
    long_term = []

    for t in tasks:
        if t.is_done or not t.due_date:
            continue
        try:
            due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
            if due >= threshold_date:
                long_term.append(t)
        except ValueError:
            pass

    return long_term


# ==================== 阶段详情增强 ====================

def get_phase_detail(db: Database, project_name: str, phase_id: str) -> Dict:
    """获取阶段详情（包含任务统计、阻塞任务、最近更新任务）"""
    phase = get_phase(db, project_name, phase_id)
    if not phase:
        return {}

    tasks = get_phase_tasks(db, project_name, phase_id)
    done_count = len([t for t in tasks if t.is_done])
    blocked_tasks = [t for t in tasks if t.status == "blocked"]
    blocked_count = len(blocked_tasks)

    sorted_tasks = sorted(
        tasks,
        key=lambda t: _parse_date(t.updated_at) or datetime.min,
        reverse=True,
    )
    recent_tasks = sorted_tasks[:5]

    return {
        "phase": phase,
        "tasks": tasks,
        "done_count": done_count,
        "blocked_count": blocked_count,
        "blocked_tasks": blocked_tasks,
        "recent_tasks": recent_tasks,
    }
