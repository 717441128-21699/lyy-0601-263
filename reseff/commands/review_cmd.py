"""review 命令 - 回顾与统计"""
import click
from typing import Optional
from datetime import datetime, timedelta

from ..storage import (
    load_db, get_completion_rate, get_this_week_completion,
    get_this_week_tasks, list_papers,
    list_weekly_reports, get_weekly_report,
    normalize_weekly_metrics,
    get_all_projects_health, calc_project_health,
)
from ..utils.formatting import (
    print_completion_stats, print_week_review, print_papers,
    print_success, print_error, print_warning, print_info,
    get_status_label,
    print_weekly_reports_list, print_weekly_report_detail,
    print_monthly_overview, print_monthly_project_detail,
)


@click.group()
def review():
    """回顾与统计命令

    查看完成率、回顾本周进度、统计拖延项。
    """
    pass


@review.command()
@click.option("--project", "-p", default=None, help="按项目统计")
def rate(project: Optional[str]):
    """查看任务完成率"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    stats = get_completion_rate(db, project=project)

    if stats["total"] == 0:
        print_warning("暂无任务数据")
        return

    print_completion_stats(stats, project=project)


@review.command()
@click.option("--project", "-p", default=None, help="按项目统计")
def week(project: Optional[str]):
    """回顾本周进度

    显示本周新增、完成的任务，以及进行中的任务。
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

    week_tasks.sort(key=lambda x: x.created_at)

    if week_stats["created"] == 0 and week_stats["completed"] == 0:
        print_warning("本周暂无任务记录")
        return

    print_week_review(week_stats, week_tasks)

    if week_stats["total_active"] > 0:
        print_info(f"还有 {week_stats['total_active']} 项任务待处理")


@review.command()
@click.option("--project", "-p", default=None, help="按项目统计")
def progress(project: Optional[str]):
    """查看整体进度

    综合显示任务完成率、文献阅读进度和本周回顾。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    print_info("📊 整体进度统计")
    print()

    task_stats = get_completion_rate(db, project=project)
    if task_stats["total"] > 0:
        print_completion_stats(task_stats, project=project)
    else:
        print_warning("暂无任务数据")

    print()

    total_papers = len(db.papers)
    if project:
        papers = list_papers(db, project=project)
    else:
        papers = db.papers

    if papers:
        read = len([p for p in papers if p.status == "read"])
        reading = len([p for p in papers if p.status == "reading"])
        unread = len([p for p in papers if p.status == "unread"])
        rate = (read / len(papers) * 100) if len(papers) > 0 else 0

        from rich.panel import Panel
        from rich.console import Console
        console = Console()

        content = []
        content.append(f"[bold]总文献数:[/bold] {len(papers)}")
        content.append(f"[green]已读:[/green] {read}")
        content.append(f"[yellow]在读:[/yellow] {reading}")
        content.append(f"[dim]未读:[/dim] {unread}")
        content.append(f"[bold]阅读完成率:[/bold] {rate:.1f}%")

        title = "文献阅读进度"
        if project:
            title += f" - {project}"

        console.print(Panel("\n".join(content), title=title, expand=False))
    else:
        print_warning("暂无文献数据")

    print()

    week_stats = get_this_week_completion(db, project=project)
    if week_stats["created"] > 0 or week_stats["completed"] > 0:
        print_info(f"📅 本周: 新增 {week_stats['created']} 项, 完成 {week_stats['completed']} 项")


@review.command()
def summary():
    """显示综合统计摘要

    快速查看所有关键指标。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    from rich.table import Table
    from rich.console import Console

    console = Console()

    table = Table(title="📋 综合统计摘要", show_header=True, header_style="bold")
    table.add_column("类别", style="bold")
    table.add_column("数量", justify="right")
    table.add_column("备注", style="dim")

    total_papers = len(db.papers)
    read_papers = len([p for p in db.papers if p.status == "read"])
    table.add_row(
        "📚 文献总数",
        str(total_papers),
        f"已读 {read_papers} ({read_papers/total_papers*100:.0f}%)" if total_papers > 0 else "-"
    )

    total_tasks = len(db.tasks)
    done_tasks = len([t for t in db.tasks if t.status == "done"])
    table.add_row(
        "✅ 任务总数",
        str(total_tasks),
        f"已完成 {done_tasks} ({done_tasks/total_tasks*100:.0f}%)" if total_tasks > 0 else "-"
    )

    from ..storage import get_overdue_tasks, get_procrastinated_tasks
    overdue = get_overdue_tasks(db)
    table.add_row(
        "⚠️  逾期任务",
        str(len(overdue)),
        style="red" if overdue else "green"
    )

    procrastinated = get_procrastinated_tasks(db)
    table.add_row(
        "⏰ 拖延任务",
        str(len(procrastinated)),
        style="yellow" if procrastinated else "green"
    )

    week_stats = get_this_week_completion(db)
    table.add_row(
        "📅 本周完成",
        str(week_stats["completed"]),
        f"新增 {week_stats['created']} 项"
    )

    total_notes = len(db.notes)
    table.add_row(
        "📝 笔记总数",
        str(total_notes),
        "-"
    )

    from ..storage import list_projects
    projects = list_projects(db)
    table.add_row(
        "📁 活跃项目",
        str(len(projects)),
        "-"
    )

    console.print(table)

    print()
    task_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
    paper_rate = (read_papers / total_papers * 100) if total_papers > 0 else 0

    if task_rate >= 80 and paper_rate >= 80:
        print_success("🌟 进度优秀，继续保持！")
    elif task_rate >= 50 or paper_rate >= 50:
        print_info("💪 进展不错，继续努力！")
    else:
        print_warning("📌 需要加快进度了，加油！")

    reports = list_weekly_reports(db)
    if reports:
        latest = reports[-1]
        print()
        print_info(f"📄 最近周报: {latest.title} ({latest.start_date} ~ {latest.end_date})")
        if latest.metrics:
            nm = normalize_weekly_metrics(latest.metrics)
            print_info(f"   任务 {nm['completed_tasks']}/{nm['total_tasks']} "
                       f"(完成率 {nm['task_completion_rate']:.1f}%) | "
                       f"文献 {nm['read_papers']}/{nm['total_papers']} "
                       f"(阅读完成率 {nm['paper_completion_rate']:.1f}%)")


@review.command()
@click.option("--project", "-p", default=None, help="按项目筛选")
def reports(project: Optional[str]):
    """列出周报历史记录"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    reports_list = list_weekly_reports(db, project=project)
    if not reports_list:
        print_warning("暂无周报历史记录")
        return

    print_weekly_reports_list(reports_list, project=project)


@review.command(name="show-report")
@click.argument("report_id")
def show_report(report_id: str):
    """查看单条周报详情"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    report = get_weekly_report(db, report_id)
    if not report:
        print_error(f"未找到周报 ID: {report_id}")
        return

    print_weekly_report_detail(report)


@review.command()
@click.option("--project", "-p", default=None, help="按项目筛选")
def trend(project: Optional[str]):
    """查看关键指标变化趋势（最近5份周报）"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    reports_list = list_weekly_reports(db, project=project)
    if not reports_list:
        print_warning("暂无周报历史记录，无法查看趋势")
        return

    recent_reports = reports_list[-5:] if len(reports_list) >= 5 else reports_list

    from rich.table import Table
    from rich.console import Console
    from rich.text import Text

    console = Console()

    table = Table(title=f"📈 指标变化趋势（最近 {len(recent_reports)} 份周报）", show_header=True, header_style="bold")
    table.add_column("时间范围", style="bold", width=22)
    table.add_column("任务完成", justify="center")
    table.add_column("任务完成率", justify="center")
    table.add_column("文献阅读", justify="center")
    table.add_column("阅读完成率", justify="center")
    table.add_column("实验", justify="center")

    for report in recent_reports:
        nm = normalize_weekly_metrics(report.metrics or {})

        task_text = f"{nm['completed_tasks']}/{nm['total_tasks']}"
        task_rate = nm['task_completion_rate']
        tr_style = "green" if task_rate >= 70 else ("yellow" if task_rate >= 40 else "red")

        paper_text = f"{nm['read_papers']}/{nm['total_papers']}"
        paper_rate = nm['paper_completion_rate']
        pr_style = "green" if paper_rate >= 70 else ("yellow" if paper_rate >= 40 else "red")

        exp_text = f"{nm['completed_experiments']}/{nm['total_experiments']}"

        time_range = f"{report.start_date}~{report.end_date[5:]}"
        table.add_row(
            time_range,
            task_text,
            Text(f"{task_rate:.1f}%", style=tr_style),
            paper_text,
            Text(f"{paper_rate:.1f}%", style=pr_style),
            exp_text,
        )

    console.print(table)


@review.command()
@click.option("--project", "-p", default=None, help="按项目查看详细健康分析，不指定则显示全项目概览")
def monthly(project: Optional[str]):
    """月度复盘 - 项目健康概览

    综合最近几周周报、阶段推进、阻塞情况和停滞实验，
    计算健康度得分，并给出推进/暂停/归档建议。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    if project:
        health = calc_project_health(db, project)
        if not health:
            print_error(f"未找到项目: {project}")
            return
        print_monthly_project_detail(health)
    else:
        all_health = get_all_projects_health(db)
        if not all_health:
            print_warning("暂无活跃项目")
            return
        print_monthly_overview(all_health)

        if len(all_health) <= 3:
            for h in all_health:
                print()
                print_monthly_project_detail(h)
