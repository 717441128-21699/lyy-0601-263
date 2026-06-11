"""task 命令 - 任务管理"""
import click
from typing import Optional
from datetime import datetime

from ..models import Task, SubTask, Project
from ..storage import (
    load_db, add_task, get_task, update_task, delete_task,
    list_tasks, get_procrastinated_tasks, get_overdue_tasks,
    add_subtask, toggle_subtask, get_paper, get_project, add_project,
)
from ..utils.formatting import (
    print_tasks, print_task_detail, print_success, print_error,
    print_warning, get_status_label,
)


def parse_date(date_str: str) -> Optional[str]:
    """解析日期字符串，返回 YYYY-MM-DD 格式"""
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d",
        "%m/%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt in ["%m-%d", "%m/%d"]:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


@click.group()
def task():
    """任务管理命令

    用于管理待办事项、实验任务和项目进度。
    """
    pass


@task.command()
@click.option("--title", "-t", required=True, help="任务标题")
@click.option("--description", "-d", default="", help="任务描述")
@click.option("--project", "-p", default="", help="所属项目")
@click.option("--priority", "-r", default="medium",
              type=click.Choice(["low", "medium", "high"]),
              help="优先级")
@click.option("--due", "-e", default=None, help="截止日期 (YYYY-MM-DD)")
@click.option("--experiment/--no-experiment", default=False,
              help="是否为实验相关任务")
@click.option("--paper", default=None, help="关联的文献ID")
@click.option("--tag", multiple=True, help="标签（可多次指定）")
def add(title: str, description: str, project: str, priority: str,
        due: Optional[str], experiment: bool, paper: Optional[str], tag):
    """添加新任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    due_date = parse_date(due)
    if due and not due_date:
        print_error(f"日期格式无效: {due}，请使用 YYYY-MM-DD 格式")
        return

    if project and not get_project(db, project):
        add_project(db, Project(name=project))
        print_success(f"已自动创建新项目: {project}")

    if paper and not get_paper(db, paper):
        print_error(f"未找到 ID 为 {paper} 的文献")
        return

    tags = list(tag)
    task = Task(
        title=title,
        description=description,
        project=project,
        priority=priority,
        due_date=due_date,
        experiment_related=experiment,
        paper_id=paper,
        tags=tags,
    )

    add_task(db, task)
    print_success(f"任务添加成功: [{task.id}] {task.title}")


@task.command(name="list")
@click.option("--project", "-p", default=None, help="按项目筛选")
@click.option("--status", "-s", default=None,
              type=click.Choice(["todo", "doing", "done", "blocked"]),
              help="按状态筛选")
@click.option("--priority", "-r", default=None,
              type=click.Choice(["low", "medium", "high"]),
              help="按优先级筛选")
@click.option("--experiment", "-e", is_flag=True, help="仅显示实验相关任务")
def list_cmd(project: Optional[str], status: Optional[str],
             priority: Optional[str], experiment: bool):
    """列出所有任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    tasks = list_tasks(
        db,
        project=project,
        status=status,
        priority=priority,
        experiment_only=experiment,
    )

    if not tasks:
        print_warning("暂无任务记录")
        return

    title = "任务列表"
    filters = []
    if project:
        filters.append(f"项目: {project}")
    if status:
        filters.append(f"状态: {get_status_label(status)}")
    if priority:
        filters.append(f"优先级: {priority}")
    if experiment:
        filters.append("仅实验相关")
    if filters:
        title += " - " + " | ".join(filters)

    print_tasks(tasks, title=title)


@task.command()
@click.argument("id")
def show(id: str):
    """查看任务详情"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, id)
    if not task:
        print_error(f"未找到 ID 为 {id} 的任务")
        return

    print_task_detail(task)


@task.command()
@click.argument("id")
@click.option("--title", default=None, help="更新标题")
@click.option("--description", "-d", default=None, help="更新描述")
@click.option("--project", "-p", default=None, help="更新项目")
@click.option("--priority", "-r", default=None,
              type=click.Choice(["low", "medium", "high"]),
              help="更新优先级")
@click.option("--status", "-s", default=None,
              type=click.Choice(["todo", "doing", "done", "blocked"]),
              help="更新状态")
@click.option("--due", "-e", default=None, help="更新截止日期")
@click.option("--tag", multiple=True, help="添加标签（可多次指定）")
def update(id: str, title: Optional[str], description: Optional[str],
           project: Optional[str], priority: Optional[str],
           status: Optional[str], due: Optional[str], tag):
    """更新任务信息"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, id)
    if not task:
        print_error(f"未找到 ID 为 {id} 的任务")
        return

    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if description is not None:
        kwargs["description"] = description
    if project is not None:
        kwargs["project"] = project
        if project and not get_project(db, project):
            add_project(db, __import__('..models', fromlist=['Project']).Project(name=project))
            print_success(f"已自动创建新项目: {project}")
    if priority is not None:
        kwargs["priority"] = priority
    if status is not None:
        kwargs["status"] = status
    if due is not None:
        due_date = parse_date(due)
        if not due_date:
            print_error(f"日期格式无效: {due}，请使用 YYYY-MM-DD 格式")
            return
        kwargs["due_date"] = due_date
    if tag:
        new_tags = list(set(task.tags + list(tag)))
        kwargs["tags"] = new_tags

    if not kwargs:
        print_warning("未指定任何更新内容")
        return

    updated = update_task(db, id, **kwargs)
    if updated:
        print_success(f"任务更新成功: [{id}]")


@task.command(name="status")
@click.argument("id")
@click.argument("new_status",
                type=click.Choice(["todo", "doing", "done", "blocked"]))
def set_status(id: str, new_status: str):
    """快速标记任务状态

    NEW_STATUS: todo|doing|done|blocked
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, id)
    if not task:
        print_error(f"未找到 ID 为 {id} 的任务")
        return

    update_task(db, id, status=new_status)
    print_success(f"任务状态已更新为: {get_status_label(new_status)}")


@task.command()
@click.argument("id")
@click.argument("subtask_title")
def subtask(id: str, subtask_title: str):
    """添加子任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, id)
    if not task:
        print_error(f"未找到 ID 为 {id} 的任务")
        return

    subtask = SubTask(title=subtask_title)
    result = add_subtask(db, id, subtask)

    if result:
        print_success(f"子任务已添加: [{result.id}] {result.title}")


@task.command(name="toggle-subtask")
@click.argument("task_id")
@click.argument("subtask_id")
def toggle_subtask_cmd(task_id: str, subtask_id: str):
    """切换子任务完成状态"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, task_id)
    if not task:
        print_error(f"未找到 ID 为 {task_id} 的任务")
        return

    result = toggle_subtask(db, task_id, subtask_id)
    if result:
        status = "已完成" if result.done else "未完成"
        print_success(f"子任务状态: {status}")
    else:
        print_error(f"未找到子任务 ID: {subtask_id}")


@task.command()
def procrastinated():
    """列出可能被拖延的任务

    显示逾期任务或创建超过7天仍未完成的任务。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    tasks = get_procrastinated_tasks(db)

    if not tasks:
        print_success("太棒了！没有拖延的任务 🎉")
        return

    print_tasks(tasks, title=f"拖延任务统计 ({len(tasks)} 项)")
    print_warning("这些任务可能需要你的关注")


@task.command()
def overdue():
    """列出已逾期的任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    tasks = get_overdue_tasks(db)

    if not tasks:
        print_success("太棒了！没有逾期的任务 🎉")
        return

    print_tasks(tasks, title=f"逾期任务 ({len(tasks)} 项)")


@task.command()
@click.argument("id")
@click.option("--yes", is_flag=True, help="确认删除，无需提示")
def delete(id: str, yes: bool):
    """删除任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task = get_task(db, id)
    if not task:
        print_error(f"未找到 ID 为 {id} 的任务")
        return

    if not yes:
        click.confirm(f"确定要删除任务 '{task.title}' 吗?", abort=True)

    delete_task(db, id)
    print_success(f"任务已删除: [{id}]")
