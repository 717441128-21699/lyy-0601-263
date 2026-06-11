"""plan 命令 - 计划与安排"""
import click
from typing import Optional
from datetime import datetime, timedelta

from ..models import Phase, Milestone
from ..storage import (
    load_db, get_today_tasks, list_tasks, list_papers,
    get_project, list_projects,
    add_phase, get_phase, update_phase, delete_phase,
    add_milestone, get_milestone, update_milestone, delete_milestone,
    get_phase_tasks, get_blocked_tasks_in_phase, get_project_progress,
    get_current_phase, ensure_project,
)
from ..utils.formatting import (
    print_tasks, print_papers, print_projects,
    print_success, print_error, print_warning, print_info,
    print_phases, print_milestones, print_project_detail,
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

    progress = get_project_progress(db, project_name)
    print_project_detail(project, progress)

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


# ==================== phase 子命令组 ====================

@plan.group()
def phase():
    """项目阶段管理"""
    pass


@phase.command(name="add")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--name", "-n", required=True, help="阶段名称")
@click.option("--description", "-d", default="", help="阶段描述")
@click.option("--order", type=int, default=0, help="阶段顺序（默认0，自动追加）")
@click.option("--target", default=None, help="目标日期 (YYYY-MM-DD)")
def phase_add(project: str, name: str, description: str, order: int, target: Optional[str]):
    """添加项目阶段"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    ensure_project(db, project)

    target_date = parse_date(target)
    if target and not target_date:
        print_error(f"日期格式无效: {target}，请使用 YYYY-MM-DD 格式")
        return

    phase = Phase(
        name=name,
        description=description,
        order=order,
        target_date=target_date,
    )

    result = add_phase(db, project, phase)
    if result:
        print_success(f"阶段添加成功: [{result.id}] {result.name}")


@phase.command(name="list")
@click.option("--project", "-p", required=True, help="项目名称")
def phase_list(project: str):
    """列出项目所有阶段"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    proj = get_project(db, project)
    if not proj:
        print_error(f"未找到项目: {project}")
        return

    if not proj.phases:
        print_warning(f"项目 '{project}' 暂无阶段")
        return

    print_phases(proj.phases, project)


@phase.command(name="show")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "phase_id", required=True, help="阶段ID")
def phase_show(project: str, phase_id: str):
    """查看阶段详情和关联任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    phase = get_phase(db, project, phase_id)
    if not phase:
        print_error(f"未找到阶段 ID: {phase_id}")
        return

    content = []
    content.append(f"[bold]阶段名称:[/bold] {phase.name}")
    content.append(f"[bold]描述:[/bold] {phase.description or '-'}")
    content.append(f"[bold]顺序:[/bold] {phase.order}")
    from ..utils.formatting import get_phase_status_label, get_phase_status_style
    status_style = get_phase_status_style(phase.status)
    status_label = get_phase_status_label(phase.status)
    content.append(f"[bold]状态:[/bold] [{status_style}]{status_label}[/]")
    content.append(f"[bold]目标日期:[/bold] {phase.target_date or '-'}")
    content.append(f"[bold]完成日期:[/bold] {phase.done_at or '-'}")
    content.append("")
    content.append(f"[dim]创建: {phase.created_at} | 更新: {phase.updated_at}[/]")

    from rich.panel import Panel
    from rich.console import Console
    console = Console()
    console.print(Panel("\n".join(content), title=f"阶段详情 [{phase.id}]", expand=False))

    phase_tasks = get_phase_tasks(db, project, phase_id)
    if phase_tasks:
        print_tasks(phase_tasks, title=f"阶段关联任务 ({len(phase_tasks)})")
    else:
        print_warning("该阶段暂无关联任务")


@phase.command(name="update")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "phase_id", required=True, help="阶段ID")
@click.option("--name", "-n", default=None, help="更新阶段名称")
@click.option("--description", "-d", default=None, help="更新阶段描述")
@click.option("--order", type=int, default=None, help="更新阶段顺序")
@click.option("--target", default=None, help="更新目标日期 (YYYY-MM-DD)")
def phase_update(project: str, phase_id: str, name: Optional[str],
                 description: Optional[str], order: Optional[int],
                 target: Optional[str]):
    """更新阶段信息"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    phase = get_phase(db, project, phase_id)
    if not phase:
        print_error(f"未找到阶段 ID: {phase_id}")
        return

    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if order is not None:
        kwargs["order"] = order
    if target is not None:
        target_date = parse_date(target)
        if not target_date:
            print_error(f"日期格式无效: {target}，请使用 YYYY-MM-DD 格式")
            return
        kwargs["target_date"] = target_date

    if not kwargs:
        print_warning("未指定任何更新内容")
        return

    updated = update_phase(db, project, phase_id, **kwargs)
    if updated:
        print_success(f"阶段更新成功: [{phase_id}]")


@phase.command(name="status")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "phase_id", required=True, help="阶段ID")
@click.option("--status", required=True,
              type=click.Choice(["pending", "active", "done", "blocked"]),
              help="阶段状态")
def phase_status(project: str, phase_id: str, status: str):
    """设置阶段状态"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    phase = get_phase(db, project, phase_id)
    if not phase:
        print_error(f"未找到阶段 ID: {phase_id}")
        return

    updated = update_phase(db, project, phase_id, status=status)
    if updated:
        from ..utils.formatting import get_phase_status_label
        print_success(f"阶段状态已更新为: {get_phase_status_label(status)}")


@phase.command(name="blocked")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "phase_id", required=True, help="阶段ID")
def phase_blocked(project: str, phase_id: str):
    """查看阶段中阻塞的任务"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    phase = get_phase(db, project, phase_id)
    if not phase:
        print_error(f"未找到阶段 ID: {phase_id}")
        return

    blocked_tasks = get_blocked_tasks_in_phase(db, project, phase_id)
    if not blocked_tasks:
        print_success("该阶段没有阻塞的任务 🎉")
        return

    print_tasks(blocked_tasks, title=f"阶段阻塞任务 ({len(blocked_tasks)})")


@phase.command(name="delete")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "phase_id", required=True, help="阶段ID")
@click.option("--yes", is_flag=True, help="确认删除，无需提示")
def phase_delete(project: str, phase_id: str, yes: bool):
    """删除阶段"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    phase = get_phase(db, project, phase_id)
    if not phase:
        print_error(f"未找到阶段 ID: {phase_id}")
        return

    if not yes:
        click.confirm(f"确定要删除阶段 '{phase.name}' 吗?", abort=True)

    deleted = delete_phase(db, project, phase_id)
    if deleted:
        print_success(f"阶段已删除: [{phase_id}]")


# ==================== milestone 子命令组 ====================

@plan.group()
def milestone():
    """项目里程碑管理"""
    pass


@milestone.command(name="add")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--name", "-n", required=True, help="里程碑名称")
@click.option("--description", "-d", default="", help="里程碑描述")
@click.option("--target", default=None, help="目标日期 (YYYY-MM-DD)")
def milestone_add(project: str, name: str, description: str, target: Optional[str]):
    """添加项目里程碑"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    ensure_project(db, project)

    target_date = parse_date(target)
    if target and not target_date:
        print_error(f"日期格式无效: {target}，请使用 YYYY-MM-DD 格式")
        return

    milestone = Milestone(
        name=name,
        description=description,
        target_date=target_date,
    )

    result = add_milestone(db, project, milestone)
    if result:
        print_success(f"里程碑添加成功: [{result.id}] {result.name}")


@milestone.command(name="list")
@click.option("--project", "-p", required=True, help="项目名称")
def milestone_list(project: str):
    """列出项目所有里程碑"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    proj = get_project(db, project)
    if not proj:
        print_error(f"未找到项目: {project}")
        return

    if not proj.milestones:
        print_warning(f"项目 '{project}' 暂无里程碑")
        return

    print_milestones(proj.milestones, project)


@milestone.command(name="show")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "milestone_id", required=True, help="里程碑ID")
def milestone_show(project: str, milestone_id: str):
    """查看里程碑详情"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    milestone = get_milestone(db, project, milestone_id)
    if not milestone:
        print_error(f"未找到里程碑 ID: {milestone_id}")
        return

    content = []
    content.append(f"[bold]里程碑名称:[/bold] {milestone.name}")
    content.append(f"[bold]描述:[/bold] {milestone.description or '-'}")
    from ..utils.formatting import get_milestone_status_label, get_milestone_status_style
    status_style = get_milestone_status_style(milestone.status)
    status_label = get_milestone_status_label(milestone.status)
    content.append(f"[bold]状态:[/bold] [{status_style}]{status_label}[/]")
    content.append(f"[bold]目标日期:[/bold] {milestone.target_date or '-'}")
    content.append(f"[bold]达成日期:[/bold] {milestone.achieved_date or '-'}")
    content.append("")
    content.append(f"[dim]创建: {milestone.created_at} | 更新: {milestone.updated_at}[/]")

    from rich.panel import Panel
    from rich.console import Console
    console = Console()
    console.print(Panel("\n".join(content), title=f"里程碑详情 [{milestone.id}]", expand=False))


@milestone.command(name="update")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "milestone_id", required=True, help="里程碑ID")
@click.option("--name", "-n", default=None, help="更新里程碑名称")
@click.option("--description", "-d", default=None, help="更新里程碑描述")
@click.option("--target", default=None, help="更新目标日期 (YYYY-MM-DD)")
def milestone_update(project: str, milestone_id: str, name: Optional[str],
                     description: Optional[str], target: Optional[str]):
    """更新里程碑信息"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    milestone = get_milestone(db, project, milestone_id)
    if not milestone:
        print_error(f"未找到里程碑 ID: {milestone_id}")
        return

    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if target is not None:
        target_date = parse_date(target)
        if not target_date:
            print_error(f"日期格式无效: {target}，请使用 YYYY-MM-DD 格式")
            return
        kwargs["target_date"] = target_date

    if not kwargs:
        print_warning("未指定任何更新内容")
        return

    updated = update_milestone(db, project, milestone_id, **kwargs)
    if updated:
        print_success(f"里程碑更新成功: [{milestone_id}]")


@milestone.command(name="status")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "milestone_id", required=True, help="里程碑ID")
@click.option("--status", required=True,
              type=click.Choice(["pending", "active", "done", "delayed"]),
              help="里程碑状态")
def milestone_status(project: str, milestone_id: str, status: str):
    """设置里程碑状态"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    milestone = get_milestone(db, project, milestone_id)
    if not milestone:
        print_error(f"未找到里程碑 ID: {milestone_id}")
        return

    updated = update_milestone(db, project, milestone_id, status=status)
    if updated:
        from ..utils.formatting import get_milestone_status_label
        print_success(f"里程碑状态已更新为: {get_milestone_status_label(status)}")


@milestone.command(name="delete")
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--id", "milestone_id", required=True, help="里程碑ID")
@click.option("--yes", is_flag=True, help="确认删除，无需提示")
def milestone_delete(project: str, milestone_id: str, yes: bool):
    """删除里程碑"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    milestone = get_milestone(db, project, milestone_id)
    if not milestone:
        print_error(f"未找到里程碑 ID: {milestone_id}")
        return

    if not yes:
        click.confirm(f"确定要删除里程碑 '{milestone.name}' 吗?", abort=True)

    deleted = delete_milestone(db, project, milestone_id)
    if deleted:
        print_success(f"里程碑已删除: [{milestone_id}]")
