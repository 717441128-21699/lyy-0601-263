"""export 命令 - 导出与归档"""
import click
import json
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..storage import (
    load_db, archive_project, list_projects,
    get_tasks_in_range, get_papers_in_range, get_experiment_progress_in_range,
    get_reminder_tasks, get_project_progress, ensure_project,
    get_completion_rate,
)
from ..models import Task, Paper
from ..utils.formatting import (
    print_success, print_error, print_warning, print_info,
    get_status_label, get_priority_label, print_reminder_tasks,
)


@click.group()
def export():
    """导出与归档命令

    导出周报、归档旧项目、提醒未完成事项。
    """
    pass


def _get_default_week_range():
    """获取本周一到周日的日期范围"""
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).date()
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")


def _parse_date_str(date_str: str) -> Optional[str]:
    """验证并标准化日期字符串为 YYYY-MM-DD"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _get_next_week_plan_tasks(db, project):
    """获取下周计划任务（即将到期的任务）"""
    now = datetime.now()
    next_week_start = (now + timedelta(days=(7 - now.weekday()))).date()
    next_week_end = next_week_start + timedelta(days=6)

    plan_tasks = []
    for t in db.tasks:
        if project and t.project != project:
            continue
        if t.is_done:
            continue
        if t.due_date:
            try:
                due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
                if next_week_start <= due <= next_week_end:
                    plan_tasks.append(t)
            except ValueError:
                continue
    return plan_tasks


def _generate_markdown_weekly(
    title, start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks
):
    lines = [f"# {title}", ""]

    lines.append("## 📊 概览")
    lines.append("")
    lines.append(f"- 新增任务: **{len(task_data['created'])}** 项")
    lines.append(f"- 完成任务: **{len(task_data['completed'])}** 项")
    lines.append(f"- 逾期任务: **{len(task_data['overdue_in_range'])}** 项")
    lines.append(f"- 实验总数: **{exp_progress['total_experiments']}** 项")
    lines.append(f"- 完成实验: **{exp_progress['completed_experiments']}** 项")
    lines.append("")

    if task_data["completed"]:
        lines.append("## ✅ 完成项")
        lines.append("")
        for t in task_data["completed"]:
            done_at = t.done_at.split()[0] if t.done_at else ""
            lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** ({done_at})")
            if t.description:
                lines.append(f"  - {t.description}")
        lines.append("")

    if task_data["overdue_in_range"]:
        lines.append("## ⚠️ 延期项")
        lines.append("")
        for t in task_data["overdue_in_range"]:
            due = t.due_date or ""
            lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** (截止: {due})")
            if t.description:
                lines.append(f"  - {t.description}")
        lines.append("")

    lines.append("## 📚 阅读进度")
    lines.append("")
    all_papers = paper_data["created"] + paper_data["read"]
    total = len(all_papers)
    read_count = len(paper_data["read"])
    rate = (read_count / total * 100) if total > 0 else 0
    lines.append(f"- 文献总数: **{total}**")
    lines.append(f"- 已读: **{read_count}**")
    lines.append(f"- 完成率: **{rate:.1f}%**")
    lines.append("")
    if all_papers:
        for p in all_papers:
            status = get_status_label(p.status)
            lines.append(f"- [{status}] **{p.title}** - {p.authors} ({p.year or 'N/A'})")
        lines.append("")

    lines.append("## 🧪 实验进展")
    lines.append("")
    lines.append(f"- 实验总数: **{exp_progress['total_experiments']}** 项")
    lines.append(f"- 已完成: **{exp_progress['completed_experiments']}** 项")
    lines.append(f"- 进行中: **{exp_progress['active_experiments']}** 项")
    lines.append("")
    all_exp = exp_progress["completed_tasks"] + exp_progress["active_tasks"]
    if all_exp:
        for t in all_exp:
            status = get_status_label(t.status)
            due = f" (截止: {t.due_date})" if t.due_date else ""
            lines.append(f"- [{status}] **{t.title}**{due}")
        lines.append("")

    if task_data["all_active"]:
        lines.append("## 📋 进行中任务")
        lines.append("")
        for t in task_data["all_active"]:
            status = get_status_label(t.status)
            due = f" (截止: {t.due_date})" if t.due_date else ""
            lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** - {status}{due}")
        lines.append("")

    if with_next_week_plan:
        lines.append("## 📅 下周计划")
        lines.append("")
        if next_week_tasks:
            lines.append("根据即将到期任务自动生成：")
            lines.append("")
            for t in next_week_tasks:
                due = t.due_date or ""
                lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** (截止: {due})")
        else:
            lines.append("暂无即将到期的任务，请自定义下周计划。")
        lines.append("")

    lines.append("---")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def _generate_text_weekly(
    title, start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks
):
    lines = [f"{'='*60}", f"{title:^60}", f"{'='*60}", ""]

    lines.append("【概览】")
    lines.append(f"  新增任务: {len(task_data['created'])} 项")
    lines.append(f"  完成任务: {len(task_data['completed'])} 项")
    lines.append(f"  逾期任务: {len(task_data['overdue_in_range'])} 项")
    lines.append(f"  实验总数: {exp_progress['total_experiments']} 项")
    lines.append(f"  完成实验: {exp_progress['completed_experiments']} 项")
    lines.append("")

    if task_data["completed"]:
        lines.append("【完成项】")
        for t in task_data["completed"]:
            done_at = t.done_at.split()[0] if t.done_at else ""
            lines.append(f"  ✓ [{get_priority_label(t.priority)}] {t.title} ({done_at})")
        lines.append("")

    if task_data["overdue_in_range"]:
        lines.append("【延期项】")
        for t in task_data["overdue_in_range"]:
            due = t.due_date or ""
            lines.append(f"  ⚠ [{get_priority_label(t.priority)}] {t.title} (截止: {due})")
        lines.append("")

    lines.append("【阅读进度】")
    all_papers = paper_data["created"] + paper_data["read"]
    total = len(all_papers)
    read_count = len(paper_data["read"])
    rate = (read_count / total * 100) if total > 0 else 0
    lines.append(f"  文献总数: {total}")
    lines.append(f"  已读: {read_count}")
    lines.append(f"  完成率: {rate:.1f}%")
    if all_papers:
        for p in all_papers:
            status = get_status_label(p.status)
            lines.append(f"  [{status}] {p.title} - {p.authors}")
    lines.append("")

    lines.append("【实验进展】")
    lines.append(f"  实验总数: {exp_progress['total_experiments']} 项")
    lines.append(f"  已完成: {exp_progress['completed_experiments']} 项")
    lines.append(f"  进行中: {exp_progress['active_experiments']} 项")
    all_exp = exp_progress["completed_tasks"] + exp_progress["active_tasks"]
    if all_exp:
        for t in all_exp:
            status = get_status_label(t.status)
            lines.append(f"  [{status}] {t.title}")
    lines.append("")

    if task_data["all_active"]:
        lines.append("【进行中任务】")
        for t in task_data["all_active"]:
            status = get_status_label(t.status)
            due = f" (截止: {t.due_date})" if t.due_date else ""
            lines.append(f"  ○ [{get_priority_label(t.priority)}] {t.title} - {status}{due}")
        lines.append("")

    if with_next_week_plan:
        lines.append("【下周计划】")
        if next_week_tasks:
            lines.append("  根据即将到期任务自动生成：")
            for t in next_week_tasks:
                due = t.due_date or ""
                lines.append(f"  - [{get_priority_label(t.priority)}] {t.title} (截止: {due})")
        else:
            lines.append("  暂无即将到期的任务，请自定义下周计划。")
        lines.append("")

    lines.append("-" * 60)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def _generate_json_weekly(
    start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks
):
    all_papers = paper_data["created"] + paper_data["read"]
    total_papers = len(all_papers)
    read_count = len(paper_data["read"])
    paper_rate = (read_count / total_papers * 100) if total_papers > 0 else 0

    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": {
            "start": start,
            "end": end,
        },
        "project": project or "全部",
        "overview": {
            "created_tasks": len(task_data["created"]),
            "completed_tasks": len(task_data["completed"]),
            "overdue_tasks": len(task_data["overdue_in_range"]),
            "total_experiments": exp_progress["total_experiments"],
            "completed_experiments": exp_progress["completed_experiments"],
        },
        "completed_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "done_at": t.done_at,
                "project": t.project,
            }
            for t in task_data["completed"]
        ],
        "overdue_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "due_date": t.due_date,
                "project": t.project,
            }
            for t in task_data["overdue_in_range"]
        ],
        "papers": {
            "total": total_papers,
            "read": read_count,
            "completion_rate": paper_rate,
            "items": [
                {
                    "id": p.id,
                    "title": p.title,
                    "authors": p.authors,
                    "year": p.year,
                    "status": p.status,
                    "project": p.project,
                }
                for p in all_papers
            ],
        },
        "experiments": {
            "total": exp_progress["total_experiments"],
            "completed": exp_progress["completed_experiments"],
            "active": exp_progress["active_experiments"],
            "items": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "due_date": t.due_date,
                    "project": t.project,
                }
                for t in (exp_progress["completed_tasks"] + exp_progress["active_tasks"])
            ],
        },
        "active_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "project": t.project,
            }
            for t in task_data["all_active"]
        ],
    }

    if with_next_week_plan:
        data["next_week_plan"] = [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "due_date": t.due_date,
                "project": t.project,
            }
            for t in next_week_tasks
        ]

    return json.dumps(data, ensure_ascii=False, indent=2)


@export.command()
@click.option("--from", "from_date", "-f", default=None, help="起始日期 YYYY-MM-DD（默认本周一）")
@click.option("--to", "to_date", "-t", default=None, help="结束日期 YYYY-MM-DD（默认本周日）")
@click.option("--project", "-p", default=None, help="项目名（可选，不选则所有项目）")
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option("--format", "--fmt", "fmt", default="markdown",
              type=click.Choice(["markdown", "text", "json"]),
              help="输出格式（默认markdown）")
@click.option("--with-next-week-plan/--no-next-week-plan", default=True,
              help="是否包含下周计划（默认 true）")
def weekly(from_date, to_date, project, output, fmt, with_next_week_plan):
    """导出周报

    生成指定时间范围内的工作进展报告，包括完成的任务、阅读的文献、实验进展等。
    """
    default_start, default_end = _get_default_week_range()

    start = from_date or default_start
    end = to_date or default_end

    if not _parse_date_str(start):
        print_error(f"无效的起始日期格式: {start}，请使用 YYYY-MM-DD")
        return
    if not _parse_date_str(end):
        print_error(f"无效的结束日期格式: {end}，请使用 YYYY-MM-DD")
        return

    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    task_data = get_tasks_in_range(db, start, end, project=project)
    paper_data = get_papers_in_range(db, start, end, project=project)
    exp_progress = get_experiment_progress_in_range(db, start, end, project=project)

    next_week_tasks = []
    if with_next_week_plan:
        next_week_tasks = _get_next_week_plan_tasks(db, project)

    project_label = project or "全部"
    title = f"周报 - {start} ~ {end} - {project_label}"

    if fmt == "markdown":
        content = _generate_markdown_weekly(
            title, start, end, project,
            task_data, paper_data, exp_progress,
            with_next_week_plan, next_week_tasks
        )
        ext = ".md"
    elif fmt == "text":
        content = _generate_text_weekly(
            title, start, end, project,
            task_data, paper_data, exp_progress,
            with_next_week_plan, next_week_tasks
        )
        ext = ".txt"
    else:
        content = _generate_json_weekly(
            start, end, project,
            task_data, paper_data, exp_progress,
            with_next_week_plan, next_week_tasks
        )
        ext = ".json"

    if not output:
        output = f"weekly_report_{start}_{end}{ext}"
    elif not output.endswith(ext):
        output += ext

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print_success(f"周报已导出到: {output_path.absolute()}")


@export.command()
@click.argument("project_name")
def archive(project_name: str):
    """归档项目

    标记项目为已归档，不再显示在默认列表中。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    project = archive_project(db, project_name)
    if project:
        print_success(f"项目已归档: {project_name}")
        print_info("归档的项目可以使用 `plan projects --all` 查看")
    else:
        print_error(f"未找到项目: {project_name}")


@export.command()
@click.option("--project", "-p", default=None, help="按项目筛选")
def remind(project: Optional[str]):
    """提醒未完成事项

    显示今天到期、即将到期、逾期和长期未处理的任务。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    reminders = get_reminder_tasks(db, project=project)
    print_reminder_tasks(reminders)


@export.command()
@click.option("--output", "-o", default="reseff_backup.json", help="备份文件路径")
def backup(output: str):
    """备份所有数据

    将所有数据导出为 JSON 备份文件。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = db.to_dict()
    data["backup_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print_success(f"数据已备份到: {output_path.absolute()}")
    print_info(f"共备份 {len(db.papers)} 篇文献, {len(db.tasks)} 个任务, {len(db.notes)} 条笔记")
