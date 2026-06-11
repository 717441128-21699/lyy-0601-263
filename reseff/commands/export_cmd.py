"""export 命令 - 导出与归档"""
import click
import json
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..storage import (
    load_db, get_this_week_completion, get_this_week_tasks,
    get_completion_rate, archive_project, list_projects,
    get_overdue_tasks, get_procrastinated_tasks,
)
from ..utils.formatting import (
    print_success, print_error, print_warning, print_info,
    get_status_label, get_priority_label,
)


@click.group()
def export():
    """导出与归档命令

    导出周报、归档旧项目、提醒未完成事项。
    """
    pass


@export.command()
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option("--project", "-p", default=None, help="按项目筛选")
@click.option("--format", "-f", default="markdown",
              type=click.Choice(["markdown", "text", "json"]),
              help="输出格式")
def weekly(output: Optional[str], project: Optional[str], format: str):
    """导出周报

    生成本周工作进展报告，包括完成的任务、阅读的文献等。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    week_stats = get_this_week_completion(db, project=project)
    week_tasks = get_this_week_tasks(db)
    if project:
        week_tasks = [t for t in week_tasks if t.project == project]

    completed_tasks = [t for t in week_tasks if t.status == "done" and t.done_at]
    in_progress_tasks = [t for t in week_tasks if t.status in ["todo", "doing"]]

    papers_this_week = []
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).date()
    for p in db.papers:
        try:
            created = datetime.strptime(p.created_at.split()[0], "%Y-%m-%d").date()
            read = None
            if p.read_at:
                read = datetime.strptime(p.read_at.split()[0], "%Y-%m-%d").date()
            if (created >= start_of_week) or (read and read >= start_of_week):
                if project and p.project != project:
                    continue
                papers_this_week.append(p)
        except (ValueError, IndexError):
            continue

    notes_this_week = []
    for n in db.notes:
        try:
            created = datetime.strptime(n.created_at.split()[0], "%Y-%m-%d").date()
            if created >= start_of_week:
                if project and n.project != project:
                    continue
                notes_this_week.append(n)
        except (ValueError, IndexError):
            continue

    completion_stats = get_completion_rate(db, project=project)

    today = datetime.now().strftime("%Y-%m-%d")
    title = f"周报 - {today}"
    if project:
        title += f" - {project}"

    if format == "markdown":
        content = _generate_markdown_weekly(
            title, week_stats, completion_stats, completed_tasks,
            in_progress_tasks, papers_this_week, notes_this_week, project
        )
        ext = ".md"
    elif format == "text":
        content = _generate_text_weekly(
            title, week_stats, completion_stats, completed_tasks,
            in_progress_tasks, papers_this_week, notes_this_week, project
        )
        ext = ".txt"
    else:
        content = _generate_json_weekly(
            week_stats, completion_stats, completed_tasks,
            in_progress_tasks, papers_this_week, notes_this_week, project
        )
        ext = ".json"

    if not output:
        output = f"weekly_report_{today}{ext}"
    elif not output.endswith(ext):
        output += ext

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print_success(f"周报已导出到: {output_path.absolute()}")


def _generate_markdown_weekly(title, week_stats, completion_stats, completed,
                              in_progress, papers, notes, project):
    lines = [f"# {title}", ""]

    lines.append("## 📊 本周概览")
    lines.append("")
    lines.append(f"- 新增任务: **{week_stats['created']}** 项")
    lines.append(f"- 完成任务: **{week_stats['completed']}** 项")
    lines.append(f"- 进行中: **{week_stats['total_active']}** 项")
    lines.append("")

    lines.append("## 📈 整体完成率")
    lines.append("")
    lines.append(f"- 总任务数: {completion_stats['total']}")
    lines.append(f"- 已完成: {completion_stats['done']}")
    lines.append(f"- 完成率: **{completion_stats['rate']:.1f}%**")
    lines.append("")

    if completed:
        lines.append("## ✅ 本周完成")
        lines.append("")
        for t in completed:
            done_at = t.done_at.split()[0] if t.done_at else ""
            lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** ({done_at})")
            if t.description:
                lines.append(f"  - {t.description}")
        lines.append("")

    if in_progress:
        lines.append("## 🚧 进行中")
        lines.append("")
        for t in in_progress:
            status = get_status_label(t.status)
            due = f" (截止: {t.due_date})" if t.due_date else ""
            lines.append(f"- [{get_priority_label(t.priority)}] **{t.title}** - {status}{due}")
        lines.append("")

    if papers:
        lines.append("## 📚 本周文献")
        lines.append("")
        for p in papers:
            status = get_status_label(p.status)
            lines.append(f"- [{status}] **{p.title}** - {p.authors} ({p.year or 'N/A'})")
            if p.summary:
                lines.append(f"  - {p.summary[:100]}...")
        lines.append("")

    if notes:
        lines.append("## 📝 本周笔记")
        lines.append("")
        for n in notes:
            paper = f" (文献: {n.paper_title})" if n.paper_title else ""
            lines.append(f"- **{n.content[:50]}...**{paper}")
        lines.append("")

    lines.append("---")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def _generate_text_weekly(title, week_stats, completion_stats, completed,
                          in_progress, papers, notes, project):
    lines = [f"{'='*60}", f"{title:^60}", f"{'='*60}", ""]

    lines.append("【本周概览】")
    lines.append(f"  新增任务: {week_stats['created']} 项")
    lines.append(f"  完成任务: {week_stats['completed']} 项")
    lines.append(f"  进行中: {week_stats['total_active']} 项")
    lines.append("")

    lines.append("【整体完成率】")
    lines.append(f"  总任务数: {completion_stats['total']}")
    lines.append(f"  已完成: {completion_stats['done']}")
    lines.append(f"  完成率: {completion_stats['rate']:.1f}%")
    lines.append("")

    if completed:
        lines.append("【本周完成】")
        for t in completed:
            done_at = t.done_at.split()[0] if t.done_at else ""
            lines.append(f"  ✓ [{get_priority_label(t.priority)}] {t.title} ({done_at})")
        lines.append("")

    if in_progress:
        lines.append("【进行中】")
        for t in in_progress:
            status = get_status_label(t.status)
            due = f" (截止: {t.due_date})" if t.due_date else ""
            lines.append(f"  ○ [{get_priority_label(t.priority)}] {t.title} - {status}{due}")
        lines.append("")

    if papers:
        lines.append("【本周文献】")
        for p in papers:
            status = get_status_label(p.status)
            lines.append(f"  [{status}] {p.title} - {p.authors}")
        lines.append("")

    if notes:
        lines.append("【本周笔记】")
        for n in notes:
            lines.append(f"  * {n.content[:60]}...")
        lines.append("")

    lines.append("-" * 60)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def _generate_json_weekly(week_stats, completion_stats, completed,
                          in_progress, papers, notes, project):
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project": project,
        "week_summary": week_stats,
        "completion_stats": completion_stats,
        "completed_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "done_at": t.done_at,
            }
            for t in completed
        ],
        "in_progress_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
            }
            for t in in_progress
        ],
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "status": p.status,
            }
            for p in papers
        ],
        "notes": [
            {
                "id": n.id,
                "content": n.content,
                "paper_title": n.paper_title,
            }
            for n in notes
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


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
def remind():
    """提醒未完成事项

    显示逾期任务和可能被拖延的任务。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    overdue = get_overdue_tasks(db)
    procrastinated = get_procrastinated_tasks(db)

    has_issues = False

    if overdue:
        has_issues = True
        print_warning(f"⚠️  有 {len(overdue)} 项任务已逾期:")
        for t in overdue:
            print(f"  • [{t.id}] {t.title} (截止: {t.due_date})")
        print()

    procrastinated_not_overdue = [t for t in procrastinated if t not in overdue]
    if procrastinated_not_overdue:
        has_issues = True
        print_warning(f"⏰ 有 {len(procrastinated_not_overdue)} 项任务可能被拖延:")
        for t in procrastinated_not_overdue:
            print(f"  • [{t.id}] {t.title} (创建于: {t.created_at.split()[0]})")
        print()

    if not has_issues:
        print_success("🎉 太棒了！没有需要提醒的事项")
    else:
        print_info("建议优先处理这些任务，祝你顺利！💪")


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
