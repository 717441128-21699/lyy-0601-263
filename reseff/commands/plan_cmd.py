"""plan 命令 - 计划与安排"""
import click
from typing import Optional
from datetime import datetime, timedelta

from ..storage import (
    load_db, get_today_tasks, list_tasks, list_papers,
    get_project, list_projects,
)
from ..utils.formatting import (
    print_tasks, print_papers, print_projects,
    print_success, print_error, print_warning, print_info,
)


@click.group()
def plan():
    """计划与安排命令

    生成今日清单、查看项目进度、规划实验安排。
    """
    pass


@plan.command()
@click.option("--include-high-priority/--no-high-priority", default=True,
              help="是否包含高优先级任务")
def today(include_high_priority: bool):
    """生成今日任务清单

    显示今天到期或未设置截止日期的待办任务。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    today_tasks = get_today_tasks(db)

    if include_high_priority:
        high_priority = list_tasks(db, priority="high", status="todo")
        high_priority = [t for t in high_priority if t not in today_tasks]
        today_tasks = today_tasks + high_priority

    if not today_tasks:
        print_success("今天没有待办任务，可以好好休息一下 ☕")
        return

    high_priority_tasks = [t for t in today_tasks if t.priority == "high"]
    medium_priority_tasks = [t for t in today_tasks if t.priority == "medium"]
    low_priority_tasks = [t for t in today_tasks if t.priority == "low"]

    today_str = datetime.now().strftime("%Y-%m-%d %A")
    print_info(f"📅 今日任务清单 - {today_str}")

    if high_priority_tasks:
        print_tasks(high_priority_tasks, title="🔴 高优先级")
    if medium_priority_tasks:
        print_tasks(medium_priority_tasks, title="🟡 中优先级")
    if low_priority_tasks:
        print_tasks(low_priority_tasks, title="🟢 低优先级")

    total = len(today_tasks)
    print_info(f"今日共 {total} 项任务，加油！💪")


@plan.command()
@click.argument("project_name", required=False)
@click.option("--tasks", is_flag=True, help="显示项目相关任务")
@click.option("--papers", is_flag=True, help="显示项目相关文献")
def project(project_name: Optional[str], tasks: bool, papers: bool):
    """按项目查看或列出所有项目

    PROJECT_NAME: 项目名称（可选，不指定则列出所有项目）
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    if not project_name:
        projects = list_projects(db)
        if not projects:
            print_warning("暂无项目，添加任务或文献时会自动创建项目")
            return
        print_projects(projects)
        return

    project = get_project(db, project_name)
    if not project:
        print_error(f"未找到项目: {project_name}")
        return

    show_all = not tasks and not papers

    if show_all or tasks:
        project_tasks = list_tasks(db, project=project_name)
        if project_tasks:
            print_tasks(project_tasks, title=f"项目任务 - {project_name}")
        else:
            print_warning(f"项目 '{project_name}' 暂无任务")

    if show_all or papers:
        project_papers = list_papers(db, project=project_name)
        if project_papers:
            print_papers(project_papers, title=f"项目文献 - {project_name}")
        else:
            print_warning(f"项目 '{project_name}' 暂无文献")


@plan.command()
def experiments():
    """查看所有实验相关任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    exp_tasks = list_tasks(db, experiment_only=True)
    exp_tasks = [t for t in exp_tasks if t.status != "done"]

    if not exp_tasks:
        print_warning("暂无进行中的实验任务")
        return

    print_tasks(exp_tasks, title="🧪 实验任务安排")


@plan.command()
@click.option("--days", type=int, default=7, help="显示未来几天的任务（默认7天）")
def upcoming(days: int):
    """查看即将到期的任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    upcoming_tasks = []
    for t in db.tasks:
        if t.status == "done" or not t.due_date:
            continue
        try:
            due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
            if today <= due <= end_date:
                upcoming_tasks.append((due, t))
        except ValueError:
            continue

    upcoming_tasks.sort(key=lambda x: x[0])

    if not upcoming_tasks:
        print_success(f"未来 {days} 天没有待办任务 🎉")
        return

    tasks = [t for _, t in upcoming_tasks]
    print_tasks(tasks, title=f"📆 未来 {days} 天任务")


@plan.command()
@click.option("--all", "-a", is_flag=True, help="显示所有项目（包括已归档）")
def projects(all: bool):
    """列出所有项目"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    projects = list_projects(db, include_archived=all)
    if not projects:
        print_warning("暂无项目，添加任务或文献时会自动创建项目")
        return

    print_projects(projects)
