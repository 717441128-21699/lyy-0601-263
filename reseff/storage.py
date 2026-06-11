"""数据存储模块"""
import json
import os
from pathlib import Path
from typing import List, Optional, TypeVar, Callable
from datetime import datetime, timedelta

from .models import (
    Database, Paper, Note, Task, Project, SubTask,
    _now_str,
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


def load_db() -> Database:
    """从文件加载数据库"""
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在，请先运行 init 命令: {db_path}")

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = [Paper(**p) for p in data.get("papers", [])]
    notes = [Note(**n) for n in data.get("notes", [])]

    tasks = []
    for t in data.get("tasks", []):
        subtasks = [SubTask(**st) for st in t.get("subtasks", [])]
        t["subtasks"] = subtasks
        tasks.append(Task(**t))

    projects = [Project(**p) for p in data.get("projects", [])]

    return Database(
        papers=papers,
        notes=notes,
        tasks=tasks,
        projects=projects,
        initialized_at=data.get("initialized_at", _now_str()),
        last_updated=data.get("last_updated", _now_str()),
    )


def _find_by_id(items: List[T], id: str) -> Optional[T]:
    """通过ID查找项"""
    for item in items:
        if item.id == id:
            return item
    return None


def _filter_items(items: List[T], predicate: Callable[[T], bool]) -> List[T]:
    """过滤项"""
    return [item for item in items if predicate(item)]


def add_paper(db: Database, paper: Paper) -> Paper:
    """添加文献"""
    db.papers.append(paper)
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
        paper.updated_at = _now_str()
        save_db(db)
    return paper


def delete_paper(db: Database, id: str) -> bool:
    """删除文献"""
    paper = _find_by_id(db.papers, id)
    if paper:
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


def add_note(db: Database, note: Note) -> Note:
    """添加笔记"""
    db.notes.append(note)
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
        note.updated_at = _now_str()
        save_db(db)
    return note


def delete_note(db: Database, id: str) -> bool:
    """删除笔记"""
    note = _find_by_id(db.notes, id)
    if note:
        db.notes.remove(note)
        save_db(db)
        return True
    return False


def list_notes(db: Database, paper_id: Optional[str] = None, project: Optional[str] = None) -> List[Note]:
    """列出笔记"""
    notes = db.notes
    if paper_id:
        notes = [n for n in notes if n.paper_id == paper_id]
    if project:
        notes = [n for n in notes if n.project == project]
    return notes


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


def add_task(db: Database, task: Task) -> Task:
    """添加任务"""
    db.tasks.append(task)
    save_db(db)
    return task


def get_task(db: Database, id: str) -> Optional[Task]:
    """获取任务"""
    return _find_by_id(db.tasks, id)


def update_task(db: Database, id: str, **kwargs) -> Optional[Task]:
    """更新任务"""
    task = _find_by_id(db.tasks, id)
    if task:
        for key, value in kwargs.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        task.updated_at = _now_str()
        if task.status == "done" and not task.done_at:
            task.done_at = _now_str()
        save_db(db)
    return task


def delete_task(db: Database, id: str) -> bool:
    """删除任务"""
    task = _find_by_id(db.tasks, id)
    if task:
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


def get_today_tasks(db: Database) -> List[Task]:
    """获取今日任务"""
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        t for t in db.tasks
        if t.status != "done"
        and (t.due_date == today or not t.due_date)
    ]


def get_overdue_tasks(db: Database) -> List[Task]:
    """获取逾期任务"""
    return [t for t in db.tasks if t.is_overdue]


def get_procrastinated_tasks(db: Database) -> List[Task]:
    """获取拖延任务"""
    return [t for t in db.tasks if t.is_procrastinated]


def get_this_week_tasks(db: Database) -> List[Task]:
    """获取本周任务"""
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)

    result = []
    for t in db.tasks:
        try:
            created = datetime.strptime(t.created_at.split()[0], "%Y-%m-%d").date()
            done = None
            if t.done_at:
                done = datetime.strptime(t.done_at.split()[0], "%Y-%m-%d").date()
            if (start_of_week <= created <= end_of_week) or (done and start_of_week <= done <= end_of_week):
                result.append(t)
        except (ValueError, IndexError):
            continue
    return result


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

    return {
        "total": total,
        "done": done,
        "doing": doing,
        "todo": todo,
        "blocked": blocked,
        "overdue": overdue,
        "procrastinated": procrastinated,
        "rate": (done / total * 100) if total > 0 else 0,
    }


def get_this_week_completion(db: Database, project: Optional[str] = None) -> dict:
    """获取本周完成率"""
    tasks = get_this_week_tasks(db)
    if project:
        tasks = [t for t in tasks if t.project == project]

    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).date()

    completed_this_week = [
        t for t in tasks
        if t.status == "done" and t.done_at
        and datetime.strptime(t.done_at.split()[0], "%Y-%m-%d").date() >= start_of_week
    ]

    created_this_week = [
        t for t in tasks
        if datetime.strptime(t.created_at.split()[0], "%Y-%m-%d").date() >= start_of_week
    ]

    return {
        "created": len(created_this_week),
        "completed": len(completed_this_week),
        "total_active": len([t for t in tasks if t.status != "done"]),
    }
