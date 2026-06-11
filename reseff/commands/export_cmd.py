"""export 命令 - 导出与归档"""
import click
import json
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..storage import (
    load_db, archive_project, list_projects,
    get_tasks_in_range, get_papers_in_range_dedup, get_experiment_progress_in_range,
    get_reminder_tasks, get_project_progress, ensure_project,
    get_completion_rate, add_weekly_report, get_weekly_report,
    list_weekly_reports, delete_weekly_report, get_long_term_tasks,
    get_coming_soon_tasks, get_long_pending_tasks,
)
from ..models import Task, Paper, WeeklyReport
from ..utils.formatting import (
    print_success, print_error, print_warning, print_info,
    get_status_label, get_priority_label, print_reminder_tasks,
    print_weekly_reports_list, print_weekly_report_detail,
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


def _priority_sort_key(task):
    """优先级排序键：high > medium > low"""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return priority_order.get(task.priority, 1)


def _get_next_week_plan_tasks(db, project):
    """获取下周计划任务（从即将到期和远期任务中提取，按优先级排序）"""
    coming_soon = get_coming_soon_tasks(db, project=project)
    long_term = get_long_term_tasks(db, project=project)

    seen_ids = set()
    plan_tasks = []

    for t in coming_soon:
        if t.id not in seen_ids:
            seen_ids.add(t.id)
            plan_tasks.append(t)

    for t in long_term:
        if t.id not in seen_ids:
            seen_ids.add(t.id)
            plan_tasks.append(t)

    plan_tasks.sort(key=_priority_sort_key)
    return plan_tasks


def _calc_weekly_stats(task_data, paper_data, exp_progress):
    """统一计算周报统计数据，确保所有格式输出一致

    任务总数 = 周末未完成任务 + 本周完成任务（去重后，本周涉及的所有任务）
    阅读进度 = 去重后的文献统计
    """
    active_count = len(task_data["all_active"])
    completed_count = len(task_data["completed"])
    overdue_count = len(task_data["overdue_in_range"])
    created_count = len(task_data["created"])
    total_tasks = active_count + completed_count

    task_completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0

    total_papers = paper_data.get("total_unique", 0)
    read_papers = paper_data.get("read_unique", 0)
    paper_rate = (read_papers / total_papers * 100) if total_papers > 0 else 0

    total_experiments = exp_progress.get("total_experiments", 0)
    completed_experiments = exp_progress.get("completed_experiments", 0)
    active_experiments = exp_progress.get("active_experiments", 0)

    return {
        "tasks": {
            "total": total_tasks,
            "created": created_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "active": active_count,
            "completion_rate": task_completion_rate,
        },
        "papers": {
            "total": total_papers,
            "read": read_papers,
            "completion_rate": paper_rate,
        },
        "experiments": {
            "total": total_experiments,
            "completed": completed_experiments,
            "active": active_experiments,
        },
    }


def _generate_markdown_weekly(
    title, start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks,
    detail_level="full"
):
    lines = [f"# {title}", ""]

    stats = _calc_weekly_stats(task_data, paper_data, exp_progress)
    t_stats = stats["tasks"]
    p_stats = stats["papers"]
    e_stats = stats["experiments"]

    lines.append("## 📊 概览")
    lines.append("")
    lines.append(f"- 总任务数: **{t_stats['total']}** 项")
    lines.append(f"- 完成任务: **{t_stats['completed']}** 项")
    lines.append(f"- 逾期任务: **{t_stats['overdue']}** 项")
    lines.append(f"- 进行中: **{t_stats['active']}** 项")
    lines.append(f"- 任务完成率: **{t_stats['completion_rate']:.1f}%**")
    lines.append(f"- 实验总数: **{e_stats['total']}** 项")
    lines.append(f"- 完成实验: **{e_stats['completed']}** 项")
    lines.append(f"- 文献总数: **{p_stats['total']}**")
    lines.append(f"- 已读文献: **{p_stats['read']}**")
    lines.append(f"- 阅读完成率: **{p_stats['completion_rate']:.1f}%**")
    lines.append("")

    if detail_level == "simple":
        if task_data["completed"]:
            lines.append("## ✅ 完成项")
            lines.append("")
            for t in task_data["completed"]:
                done_at = t.done_at.split()[0] if t.done_at else ""
                lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** ({done_at})")
            lines.append("")

        if with_next_week_plan:
            lines.append("## 📅 下周计划")
            lines.append("")
            if next_week_tasks:
                lines.append("根据优先级自动生成：")
                lines.append("")
                for t in next_week_tasks:
                    due = t.due_date or ""
                    lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** (截止: {due})")
            else:
                lines.append("暂无计划任务，请自定义下周计划。")
            lines.append("")

        lines.append("---")
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

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
    lines.append(f"- 文献总数: **{p_stats['total']}**")
    lines.append(f"- 已读: **{p_stats['read']}**")
    lines.append(f"- 完成率: **{p_stats['completion_rate']:.1f}%**")
    lines.append("")
    all_papers_list = paper_data.get("all_papers", [])
    if all_papers_list:
        for paper in all_papers_list:
            status = get_status_label(paper.status)
            lines.append(f"- [{status}] **{paper.title}** - {paper.authors} ({paper.year or 'N/A'})")
        lines.append("")

    lines.append("## 🧪 实验进展")
    lines.append("")
    lines.append(f"- 实验总数: **{e_stats['total']}** 项")
    lines.append(f"- 已完成: **{e_stats['completed']}** 项")
    lines.append(f"- 进行中: **{e_stats['active']}** 项")
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
            lines.append("根据即将到期和远期任务按优先级自动生成：")
            lines.append("")
            for t in next_week_tasks:
                due = t.due_date or ""
                lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** (截止: {due})")
        else:
            lines.append("暂无计划任务，请自定义下周计划。")
        lines.append("")

    lines.append("---")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def _generate_text_weekly(
    title, start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks,
    detail_level="full"
):
    lines = [f"{'='*60}", f"{title:^60}", f"{'='*60}", ""]

    stats = _calc_weekly_stats(task_data, paper_data, exp_progress)
    t_stats = stats["tasks"]
    p_stats = stats["papers"]
    e_stats = stats["experiments"]

    lines.append("【概览】")
    lines.append(f"  总任务数: {t_stats['total']} 项")
    lines.append(f"  完成任务: {t_stats['completed']} 项")
    lines.append(f"  逾期任务: {t_stats['overdue']} 项")
    lines.append(f"  进行中: {t_stats['active']} 项")
    lines.append(f"  任务完成率: {t_stats['completion_rate']:.1f}%")
    lines.append(f"  实验总数: {e_stats['total']} 项")
    lines.append(f"  完成实验: {e_stats['completed']} 项")
    lines.append(f"  文献总数: {p_stats['total']}")
    lines.append(f"  已读文献: {p_stats['read']}")
    lines.append(f"  阅读完成率: {p_stats['completion_rate']:.1f}%")
    lines.append("")

    if detail_level == "simple":
        if task_data["completed"]:
            lines.append("【完成项】")
            for t in task_data["completed"]:
                done_at = t.done_at.split()[0] if t.done_at else ""
                lines.append(f"  ✓ [{get_priority_label(t.priority)}] {t.title} ({done_at})")
            lines.append("")

        if with_next_week_plan:
            lines.append("【下周计划】")
            if next_week_tasks:
                lines.append("  根据优先级自动生成：")
                for t in next_week_tasks:
                    due = t.due_date or ""
                    lines.append(f"  - [{get_priority_label(t.priority)}] {t.title} (截止: {due})")
            else:
                lines.append("  暂无计划任务，请自定义下周计划。")
            lines.append("")

        lines.append("-" * 60)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

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
    lines.append(f"  文献总数: {p_stats['total']}")
    lines.append(f"  已读: {p_stats['read']}")
    lines.append(f"  完成率: {p_stats['completion_rate']:.1f}%")
    all_papers_list = paper_data.get("all_papers", [])
    if all_papers_list:
        for paper in all_papers_list:
            status = get_status_label(paper.status)
            lines.append(f"  [{status}] {paper.title} - {paper.authors}")
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
            lines.append("  根据即将到期和远期任务按优先级自动生成：")
            for t in next_week_tasks:
                due = t.due_date or ""
                lines.append(f"  - [{get_priority_label(t.priority)}] {t.title} (截止: {due})")
        else:
            lines.append("  暂无计划任务，请自定义下周计划。")
        lines.append("")

    lines.append("-" * 60)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def _generate_json_weekly(
    start, end, project,
    task_data, paper_data, exp_progress,
    with_next_week_plan, next_week_tasks,
    detail_level="full"
):
    stats = _calc_weekly_stats(task_data, paper_data, exp_progress)
    t_stats = stats["tasks"]
    p_stats = stats["papers"]
    e_stats = stats["experiments"]
    all_papers_list = paper_data.get("all_papers", [])

    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detail_level": detail_level,
        "period": {
            "start": start,
            "end": end,
        },
        "project": project or "全部",
        "overview": {
            "total_tasks": t_stats["total"],
            "created_tasks": t_stats["created"],
            "completed_tasks": t_stats["completed"],
            "overdue_tasks": t_stats["overdue"],
            "active_tasks": t_stats["active"],
            "task_completion_rate": round(t_stats["completion_rate"], 1),
            "total_experiments": e_stats["total"],
            "completed_experiments": e_stats["completed"],
            "active_experiments": e_stats["active"],
            "total_papers": p_stats["total"],
            "read_papers": p_stats["read"],
            "paper_completion_rate": round(p_stats["completion_rate"], 1),
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
    }

    if detail_level == "full":
        data["overdue_tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "due_date": t.due_date,
                "project": t.project,
            }
            for t in task_data["overdue_in_range"]
        ]
        data["papers"] = {
            "total": p_stats["total"],
            "read": p_stats["read"],
            "completion_rate": round(p_stats["completion_rate"], 1),
            "items": [
                {
                    "id": paper_item.id,
                    "title": paper_item.title,
                    "authors": paper_item.authors,
                    "year": paper_item.year,
                    "status": paper_item.status,
                    "project": paper_item.project,
                }
                for paper_item in all_papers_list
            ],
        }
        data["experiments"] = {
            "total": e_stats["total"],
            "completed": e_stats["completed"],
            "active": e_stats["active"],
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
        }
        data["active_tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
                "project": t.project,
            }
            for t in task_data["all_active"]
        ]

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
@click.option("--detail", "--level", "detail_level", default="full",
              type=click.Choice(["simple", "full"]),
              help="周报详略级别（默认 full）")
@click.option("--save/--no-save", default=True,
              help="是否保存周报为历史记录（默认 true）")
def weekly(from_date, to_date, project, output, fmt, with_next_week_plan, detail_level, save):
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
    paper_data = get_papers_in_range_dedup(db, start, end, project=project)
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
            with_next_week_plan, next_week_tasks,
            detail_level
        )
        ext = ".md"
    elif fmt == "text":
        content = _generate_text_weekly(
            title, start, end, project,
            task_data, paper_data, exp_progress,
            with_next_week_plan, next_week_tasks,
            detail_level
        )
        ext = ".txt"
    else:
        content = _generate_json_weekly(
            start, end, project,
            task_data, paper_data, exp_progress,
            with_next_week_plan, next_week_tasks,
            detail_level
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

    if save:
        stats = _calc_weekly_stats(task_data, paper_data, exp_progress)
        t_stats = stats["tasks"]
        p_stats = stats["papers"]
        e_stats = stats["experiments"]

        metrics = {
            "total_tasks": t_stats["total"],
            "created_tasks": t_stats["created"],
            "completed_tasks": t_stats["completed"],
            "overdue_tasks": t_stats["overdue"],
            "active_tasks": t_stats["active"],
            "task_completion_rate": round(t_stats["completion_rate"], 1),
            "total_experiments": e_stats["total"],
            "completed_experiments": e_stats["completed"],
            "total_papers": p_stats["total"],
            "read_papers": p_stats["read"],
            "paper_completion_rate": round(p_stats["completion_rate"], 1),
        }

        report = WeeklyReport(
            title=title,
            project=project or "",
            start_date=start,
            end_date=end,
            format=fmt,
            detail_level=detail_level,
            content=content,
            metrics=metrics,
        )
        add_weekly_report(db, report)
        print_info(f"周报已保存为历史记录 (ID: {report.id})")


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

    显示逾期、今日到期、即将到期、远期计划、无截止日期和长期未处理的任务。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    reminders = get_reminder_tasks(db, project=project)
    long_pending = get_long_pending_tasks(db, project=project)
    reminders["long_pending"] = long_pending
    print_reminder_tasks(reminders)


@export.command("reports")
@click.option("--project", "-p", default=None, help="按项目筛选")
def reports(project: Optional[str]):
    """列出历史周报

    显示所有保存的周报历史记录。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    report_list = list_weekly_reports(db, project=project)
    if not report_list:
        print_warning("暂无周报历史记录")
        return

    print_weekly_reports_list(report_list, project=project)


@export.command("show-report")
@click.argument("report_id")
def show_report(report_id: str):
    """查看单条周报详情

    显示指定 ID 的周报详细信息和内容。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    report = get_weekly_report(db, report_id)
    if not report:
        print_error(f"未找到周报记录: {report_id}")
        return

    print_weekly_report_detail(report)


@export.command("delete-report")
@click.argument("report_id")
def delete_report(report_id: str):
    """删除单条周报

    删除指定 ID 的周报历史记录。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    success = delete_weekly_report(db, report_id)
    if success:
        print_success(f"周报已删除: {report_id}")
    else:
        print_error(f"未找到周报记录: {report_id}")


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
