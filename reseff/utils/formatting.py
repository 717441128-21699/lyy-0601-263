"""输出格式化工具"""
from typing import List, Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from ..models import Paper, Note, Task, Project, Phase, Milestone, WeeklyReport

console = Console()

STATUS_COLORS = {
    "unread": "dim",
    "reading": "yellow",
    "read": "green",
    "skipped": "strike",
    "todo": "cyan",
    "doing": "yellow",
    "done": "green",
    "blocked": "red",
}

STATUS_LABELS = {
    "unread": "未读",
    "reading": "在读",
    "read": "已读",
    "skipped": "跳过",
    "todo": "待办",
    "doing": "进行中",
    "done": "已完成",
    "blocked": "阻塞",
}

PRIORITY_COLORS = {
    "low": "dim",
    "medium": "yellow",
    "high": "red bold",
}

PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

PHASE_STATUS_COLORS = {
    "pending": "dim",
    "active": "yellow",
    "done": "green",
    "blocked": "red",
}

PHASE_STATUS_LABELS = {
    "pending": "待启动",
    "active": "进行中",
    "done": "已完成",
    "blocked": "阻塞",
}

MILESTONE_STATUS_COLORS = {
    "pending": "dim",
    "active": "yellow",
    "done": "green",
    "delayed": "red",
}

MILESTONE_STATUS_LABELS = {
    "pending": "待达成",
    "active": "进行中",
    "done": "已达成",
    "delayed": "已延期",
}


def get_phase_status_style(status: str) -> str:
    return PHASE_STATUS_COLORS.get(status, "white")


def get_phase_status_label(status: str) -> str:
    return PHASE_STATUS_LABELS.get(status, status)


def get_milestone_status_style(status: str) -> str:
    return MILESTONE_STATUS_COLORS.get(status, "white")


def get_milestone_status_label(status: str) -> str:
    return MILESTONE_STATUS_LABELS.get(status, status)


def get_status_style(status: str) -> str:
    return STATUS_COLORS.get(status, "white")


def get_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def get_priority_style(priority: str) -> str:
    return PRIORITY_COLORS.get(priority, "white")


def get_priority_label(priority: str) -> str:
    return PRIORITY_LABELS.get(priority, priority)


def print_papers(papers: List[Paper], title: str = "文献列表") -> None:
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("标题", style="bold", no_wrap=False)
    table.add_column("作者", style="dim", width=20)
    table.add_column("年份", justify="center", width=6)
    table.add_column("状态", justify="center")
    table.add_column("项目", width=15)
    table.add_column("标签", width=20)

    for p in papers:
        status_style = get_status_style(p.status)
        status_label = get_status_label(p.status)
        tags = ", ".join(p.tags[:2]) if p.tags else ""
        authors = p.authors[:18] + "..." if len(p.authors) > 18 else p.authors
        title_text = p.title[:50] + "..." if len(p.title) > 50 else p.title

        table.add_row(
            p.id,
            title_text,
            authors,
            str(p.year) if p.year else "-",
            Text(status_label, style=status_style),
            p.project or "-",
            tags or "-",
        )

    console.print(table)


def print_paper_detail(paper: Paper, notes: Optional[List[Note]] = None,
                       tasks: Optional[List[Task]] = None) -> None:
    content = []
    content.append(f"[bold]标题:[/bold] {paper.title}")
    content.append(f"[bold]作者:[/bold] {paper.authors or '-'}")
    content.append(f"[bold]年份:[/bold] {paper.year or '-'}")
    content.append(f"[bold]期刊/会议:[/bold] {paper.venue or '-'}")
    content.append(f"[bold]链接:[/bold] {paper.url or '-'}")
    content.append(f"[bold]状态:[/bold] [{get_status_style(paper.status)}]{get_status_label(paper.status)}[/]")
    content.append(f"[bold]项目:[/bold] {paper.project or '-'}")
    content.append(f"[bold]标签:[/bold] {', '.join(paper.tags) if paper.tags else '-'}")

    if paper.summary:
        content.append("")
        content.append("[bold]摘要:[/bold]")
        content.append(paper.summary)

    if paper.experiment_steps:
        content.append("")
        content.append("[bold]关联实验步骤:[/bold]")
        for i, step in enumerate(paper.experiment_steps, 1):
            content.append(f"  {i}. {step}")

    if notes:
        content.append("")
        content.append(f"[bold]关联笔记 ({len(notes)}):[/bold]")
        for n in notes:
            note_content = n.content[:40] + "..." if len(n.content) > 40 else n.content
            content.append(f"  • [{n.id}] {note_content}")
    elif notes is not None:
        content.append("")
        content.append("[bold]关联笔记:[/bold] [dim]无[/]")

    if tasks:
        content.append("")
        content.append(f"[bold]关联任务 ({len(tasks)}):[/bold]")
        for t in tasks:
            status_style = get_status_style(t.status)
            status_label = get_status_label(t.status)
            title_text = t.title[:40] + "..." if len(t.title) > 40 else t.title
            content.append(f"  • [{t.id}] [{status_style}]{status_label}[/] {title_text}")
    elif tasks is not None:
        content.append("")
        content.append("[bold]关联任务:[/bold] [dim]无[/]")

    if paper.read_at:
        content.append("")
        content.append(f"[dim]阅读时间: {paper.read_at}[/]")

    content.append("")
    content.append(f"[dim]创建: {paper.created_at} | 更新: {paper.updated_at}[/]")

    console.print(Panel("\n".join(content), title=f"文献详情 [{paper.id}]", expand=False))


def print_notes(notes: List[Note], title: str = "笔记列表") -> None:
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("内容", style="italic", no_wrap=False)
    table.add_column("关联文献", width=20)
    table.add_column("项目", width=15)
    table.add_column("标签", width=15)
    table.add_column("创建时间", style="dim", width=20)

    for n in notes:
        content = n.content[:60] + "..." if len(n.content) > 60 else n.content
        paper_title = n.paper_title[:18] + "..." if len(n.paper_title) > 18 else n.paper_title
        tags = ", ".join(n.tags[:2]) if n.tags else ""

        table.add_row(
            n.id,
            content,
            paper_title or "-",
            n.project or "-",
            tags or "-",
            n.created_at,
        )

    console.print(table)


def print_note_detail(note: Note) -> None:
    content = []
    content.append(f"[bold]关联文献:[/bold] {note.paper_title or '-'}")
    content.append(f"[bold]项目:[/bold] {note.project or '-'}")
    content.append(f"[bold]标签:[/bold] {', '.join(note.tags) if note.tags else '-'}")
    content.append("")
    content.append("[bold]内容:[/bold]")
    content.append(note.content)
    content.append("")
    content.append(f"[dim]创建: {note.created_at} | 更新: {note.updated_at}[/]")

    console.print(Panel("\n".join(content), title=f"笔记详情 [{note.id}]", expand=False))


def print_tasks(tasks: List[Task], title: str = "任务列表") -> None:
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("标题", style="bold", no_wrap=False)
    table.add_column("优先级", justify="center", width=8)
    table.add_column("状态", justify="center", width=10)
    table.add_column("截止日期", justify="center", width=12)
    table.add_column("项目", width=15)
    table.add_column("子任务", justify="center", width=8)

    for t in tasks:
        priority_style = get_priority_style(t.priority)
        priority_label = get_priority_label(t.priority)
        status_style = get_status_style(t.status)
        status_label = get_status_label(t.status)

        title_text = t.title[:45] + "..." if len(t.title) > 45 else t.title

        if t.is_overdue:
            due_style = "red bold"
            due_text = "⚠ " + (t.due_date or "")
        else:
            due_style = "white"
            due_text = t.due_date or "-"

        if t.is_procrastinated and t.status != "done":
            title_text = f"⏰ {title_text}"

        subtask_info = f"{sum(1 for s in t.subtasks if s.done)}/{len(t.subtasks)}" if t.subtasks else "-"

        table.add_row(
            t.id,
            title_text,
            Text(priority_label, style=priority_style),
            Text(status_label, style=status_style),
            Text(due_text, style=due_style),
            t.project or "-",
            subtask_info,
        )

    console.print(table)


def print_task_detail(task: Task, paper: Optional[Paper] = None,
                      notes: Optional[List[Note]] = None) -> None:
    content = []
    content.append(f"[bold]标题:[/bold] {task.title}")

    priority_style = get_priority_style(task.priority)
    priority_label = get_priority_label(task.priority)
    status_style = get_status_style(task.status)
    status_label = get_status_label(task.status)

    content.append(f"[bold]优先级:[/bold] [{priority_style}]{priority_label}[/]")
    content.append(f"[bold]状态:[/bold] [{status_style}]{status_label}[/]")
    content.append(f"[bold]截止日期:[/bold] {task.due_date or '-'}")
    content.append(f"[bold]项目:[/bold] {task.project or '-'}")
    content.append(f"[bold]实验相关:[/bold] {'是' if task.experiment_related else '否'}")
    content.append(f"[bold]标签:[/bold] {', '.join(task.tags) if task.tags else '-'}")

    if task.is_overdue:
        content.append("[red bold]⚠ 任务已逾期[/]")

    if task.is_procrastinated and task.status != "done":
        content.append("[yellow bold]⏰ 任务可能被拖延[/]")

    if paper:
        content.append("")
        content.append("[bold]关联文献:[/bold]")
        content.append(f"  [{paper.id}] {paper.title}")
        if paper.summary:
            summary_text = paper.summary[:100] + "..." if len(paper.summary) > 100 else paper.summary
            content.append(f"  [dim]{summary_text}[/]")
    elif paper is not None:
        content.append("")
        content.append("[bold]关联文献:[/bold] [dim]无[/]")

    if notes:
        content.append("")
        content.append(f"[bold]关联笔记 ({len(notes)}):[/bold]")
        for n in notes:
            note_content = n.content[:40] + "..." if len(n.content) > 40 else n.content
            content.append(f"  • [{n.id}] {note_content}")
    elif notes is not None:
        content.append("")
        content.append("[bold]关联笔记:[/bold] [dim]无[/]")

    if task.description:
        content.append("")
        content.append("[bold]描述:[/bold]")
        content.append(task.description)

    if task.subtasks:
        content.append("")
        content.append("[bold]子任务:[/bold]")
        for st in task.subtasks:
            mark = "✓" if st.done else " "
            style = "strike dim" if st.done else "white"
            content.append(f"  [{mark}] [{style}]{st.title}[/] ({st.id})")

    if task.done_at:
        content.append("")
        content.append(f"[dim]完成时间: {task.done_at}[/]")

    content.append("")
    content.append(f"[dim]创建: {task.created_at} | 更新: {task.updated_at}[/]")

    console.print(Panel("\n".join(content), title=f"任务详情 [{task.id}]", expand=False))


def print_projects(projects: List[Project], title: str = "项目列表") -> None:
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("名称", style="bold", width=25)
    table.add_column("描述", no_wrap=False)
    table.add_column("状态", justify="center", width=10)
    table.add_column("创建时间", style="dim", width=20)

    for p in projects:
        status = "已归档" if p.archived else "进行中"
        status_style = "dim strike" if p.archived else "green"

        table.add_row(
            p.id,
            p.name,
            p.description[:50] + "..." if len(p.description) > 50 else p.description,
            Text(status, style=status_style),
            p.created_at,
        )

    console.print(table)


def print_phases(phases: List[Phase], project_name: str,
                 phases_stats: Optional[Dict[str, dict]] = None) -> None:
    title = f"项目阶段列表 - {project_name}"
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("阶段名", style="bold", no_wrap=False)
    table.add_column("状态", justify="center", width=10)
    table.add_column("目标日期", justify="center", width=12)
    table.add_column("完成日期", justify="center", width=12)
    table.add_column("任务", justify="center", width=8)
    table.add_column("已完成", justify="center", width=8)
    table.add_column("阻塞", justify="center", width=8)

    for ph in sorted(phases, key=lambda x: x.order):
        status_style = get_phase_status_style(ph.status)
        status_label = get_phase_status_label(ph.status)

        if phases_stats and ph.id in phases_stats:
            stats = phases_stats[ph.id]
            total = stats.get("total", 0)
            done = stats.get("done", 0)
            blocked = stats.get("blocked", 0)
        else:
            total = len(ph.task_ids)
            done = 0
            blocked = 0

        blocked_style = "red" if blocked > 0 else "white"

        table.add_row(
            ph.id,
            ph.name,
            Text(status_label, style=status_style),
            ph.target_date or "-",
            ph.done_at or "-",
            str(total),
            Text(str(done), style="green"),
            Text(str(blocked), style=blocked_style),
        )

    console.print(table)


def print_milestones(milestones: List[Milestone], project_name: str) -> None:
    title = f"里程碑列表 - {project_name}"
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("名称", style="bold", no_wrap=False)
    table.add_column("状态", justify="center", width=10)
    table.add_column("目标日期", justify="center", width=12)
    table.add_column("达成日期", justify="center", width=12)

    for m in milestones:
        status_style = get_milestone_status_style(m.status)
        status_label = get_milestone_status_label(m.status)

        table.add_row(
            m.id,
            m.name,
            Text(status_label, style=status_style),
            m.target_date or "-",
            m.achieved_date or "-",
        )

    console.print(table)


def print_project_detail(project: Project, progress: dict) -> None:
    content = []
    content.append(f"[bold]项目名称:[/bold] {project.name}")
    content.append(f"[bold]描述:[/bold] {project.description or '-'}")
    status = "已归档" if project.archived else "进行中"
    status_style = "dim strike" if project.archived else "green"
    content.append(f"[bold]状态:[/bold] [{status_style}]{status}[/]")
    content.append(f"[bold]创建时间:[/bold] {project.created_at}")
    if project.archived_at:
        content.append(f"[bold]归档时间:[/bold] {project.archived_at}")
    content.append("")

    content.append("[bold]📊 项目进度:[/bold]")
    content.append(f"  任务: {progress.get('done_tasks', 0)}/{progress.get('total_tasks', 0)} "
                   f"({progress.get('task_completion', 0):.1f}%)")
    content.append(f"  文献: {progress.get('read_papers', 0)}/{progress.get('total_papers', 0)} "
                   f"({progress.get('paper_progress', 0):.1f}%)")
    content.append(f"  阶段: {progress.get('done_phases', 0)}/{progress.get('total_phases', 0)}")
    content.append(f"  里程碑: {progress.get('done_milestones', 0)}/{progress.get('total_milestones', 0)}")
    content.append(f"  实验: {progress.get('experiment_done', 0)}/{progress.get('experiment_count', 0)}")

    if progress.get('total_tasks', 0) > 0:
        content.append("")
        content.append("[bold]任务完成率:[/bold]")

    if project.phases:
        content.append("")
        content.append("[bold]阶段进度:[/bold]")
        for ph in sorted(project.phases, key=lambda x: x.order):
            status_style = get_phase_status_style(ph.status)
            status_label = get_phase_status_label(ph.status)
            phase_tasks = len(ph.task_ids)
            content.append(f"  [{ph.order}] [{status_style}]{status_label}[/] "
                           f"{ph.name} [dim]({phase_tasks} 个任务)[/]")

    if project.milestones:
        content.append("")
        content.append("[bold]里程碑:[/bold]")
        for m in project.milestones:
            status_style = get_milestone_status_style(m.status)
            status_label = get_milestone_status_label(m.status)
            date_info = m.target_date or "-"
            content.append(f"  • [{status_style}]{status_label}[/] {m.name} "
                           f"[dim](目标: {date_info})[/]")

    console.print(Panel("\n".join(content), title=f"项目详情 - {project.name}", expand=False))

    if progress.get('total_tasks', 0) > 0:
        progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(bar_width=30),
        )
        with progress_bar:
            task_id = progress_bar.add_task("完成进度", total=progress['total_tasks'])
            progress_bar.update(task_id, completed=progress['done_tasks'])


def print_search_results(results_dict: Dict[str, list]) -> None:
    papers = results_dict.get('papers', [])
    notes = results_dict.get('notes', [])
    tasks = results_dict.get('tasks', [])
    total = len(papers) + len(notes) + len(tasks)

    if total == 0:
        print_warning("未找到匹配的结果")
        return

    content = []
    content.append(f"[bold]共找到 {total} 条结果[/bold]")
    content.append("")

    if papers:
        content.append(f"[bold cyan]📄 文献 ({len(papers)}):[/bold cyan]")
        for p in papers:
            title_text = p.title[:60] + "..." if len(p.title) > 60 else p.title
            status_style = get_status_style(p.status)
            status_label = get_status_label(p.status)
            content.append(f"  [{p.id}] [{status_style}]{status_label}[/] {title_text}")
        content.append("")

    if notes:
        content.append(f"[bold magenta]📝 笔记 ({len(notes)}):[/bold magenta]")
        for n in notes:
            note_content = n.content[:60] + "..." if len(n.content) > 60 else n.content
            content.append(f"  [{n.id}] {note_content}")
        content.append("")

    if tasks:
        content.append(f"[bold yellow]✅ 任务 ({len(tasks)}):[/bold yellow]")
        for t in tasks:
            title_text = t.title[:60] + "..." if len(t.title) > 60 else t.title
            status_style = get_status_style(t.status)
            status_label = get_status_label(t.status)
            content.append(f"  [{t.id}] [{status_style}]{status_label}[/] {title_text}")

    console.print(Panel("\n".join(content), title="🔍 综合搜索结果", expand=False))


def print_reminder_tasks(reminders_dict: Dict[str, List[Task]]) -> None:
    today = reminders_dict.get('today', [])
    coming_soon = reminders_dict.get('coming_soon', [])
    overdue = reminders_dict.get('overdue', [])
    long_term = reminders_dict.get('long_term', [])
    no_deadline = reminders_dict.get('no_deadline', [])
    long_pending = reminders_dict.get('long_pending', [])

    total = len(today) + len(coming_soon) + len(overdue) + len(long_term) + len(no_deadline)
    if total == 0:
        print_success("太棒了！没有需要提醒的任务 🎉")
        return

    content = []
    content.append(f"[bold]共 {total} 项未完成任务[/bold]")
    content.append("")

    if overdue:
        content.append(f"[bold red]⚠ 逾期 ({len(overdue)}):[/bold red]")
        for t in overdue:
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            content.append(f"  [{t.id}] [strike]{t.due_date or '-'}[/strike] {title_text}")
        content.append("")

    if today:
        content.append(f"[bold red]📅 今天到期 ({len(today)}):[/bold red]")
        for t in today:
            priority_style = get_priority_style(t.priority)
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            content.append(f"  [{t.id}] [{priority_style}]{get_priority_label(t.priority)}[/] {title_text}")
        content.append("")

    if coming_soon:
        content.append(f"[bold yellow]⏰ 即将到期（7天内）({len(coming_soon)}):[/bold yellow]")
        for t in coming_soon:
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            content.append(f"  [{t.id}] {t.due_date or '-'} {title_text}")
        content.append("")

    if long_term:
        content.append(f"[bold cyan]📅 远期计划 ({len(long_term)}):[/bold cyan]")
        for t in long_term:
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            priority_style = get_priority_style(t.priority)
            content.append(f"  [{t.id}] [{priority_style}]{get_priority_label(t.priority)}[/] {title_text} [dim](截止: {t.due_date})[/]")
        content.append("")

    if no_deadline:
        content.append(f"[bold dim]📌 无截止日期 ({len(no_deadline)}):[/bold dim]")
        for t in no_deadline:
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            status_style = get_status_style(t.status)
            status_label = get_status_label(t.status)
            content.append(f"  [{t.id}] [{status_style}]{status_label}[/] {title_text}")
        content.append("")

    if long_pending:
        content.append(f"[bold magenta]⌛ 长期未处理（超过14天）({len(long_pending)}):[/bold magenta]")
        for t in long_pending:
            title_text = t.title[:50] + "..." if len(t.title) > 50 else t.title
            content.append(f"  [{t.id}] {title_text} [dim](创建: {t.created_at.split()[0]})[/]")

    console.print(Panel("\n".join(content), title="🔔 任务提醒", expand=False))


def print_completion_stats(stats: dict, project: str = None) -> None:
    title = f"完成率统计 - {project}" if project else "完成率统计"

    content = []
    content.append(f"[bold]总任务数:[/bold] {stats['total']}")
    content.append(f"[green]已完成:[/green] {stats['done']}")
    content.append(f"[yellow]进行中:[/yellow] {stats['doing']}")
    content.append(f"[cyan]待办:[/cyan] {stats['todo']}")
    content.append(f"[red]阻塞:[/red] {stats['blocked']}")
    content.append(f"[red bold]逾期:[/red bold] {stats['overdue']}")
    content.append(f"[yellow bold]可能拖延:[/yellow bold] {stats['procrastinated']}")
    content.append("")

    rate = stats['rate']
    if rate >= 80:
        rate_style = "green bold"
    elif rate >= 50:
        rate_style = "yellow bold"
    elif rate >= 20:
        rate_style = "yellow"
    else:
        rate_style = "red bold"

    content.append(f"[bold]完成率:[/bold] [{rate_style}]{rate:.1f}%[/]")

    if stats['total'] > 0:
        progress = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(bar_width=30),
        )
        with progress:
            task_id = progress.add_task("完成进度", total=stats['total'])
            progress.update(task_id, completed=stats['done'])

    console.print(Panel("\n".join(content), title=title, expand=False))


def print_week_review(week_stats: dict, tasks: List[Task]) -> None:
    content = []
    content.append(f"[bold]本周新增任务:[/bold] {week_stats['created']}")
    content.append(f"[bold green]本周完成任务:[/bold green] {week_stats['completed']}")
    content.append(f"[bold]进行中任务:[/bold] {week_stats['total_active']}")
    content.append("")

    if tasks:
        content.append("[bold]本周任务清单:[/bold]")
        for t in tasks:
            status = get_status_label(t.status)
            style = get_status_style(t.status)
            mark = "✓" if t.status == "done" else " "
            content.append(f"  [{mark}] [{style}]{status}[/] {t.title}")
    else:
        content.append("[dim]本周暂无任务记录[/]")

    console.print(Panel("\n".join(content), title="本周回顾", expand=False))


def print_success(msg: str) -> None:
    console.print(f"[green]✓ {msg}[/]")


def print_error(msg: str) -> None:
    console.print(f"[red]✗ {msg}[/]")


def print_warning(msg: str) -> None:
    console.print(f"[yellow]⚠ {msg}[/]")


def print_info(msg: str) -> None:
    console.print(f"[cyan]ℹ {msg}[/]")


def print_project_review(
    project: Project,
    progress: dict,
    phases_data: List[dict],
    stagnant_exp: List[Task],
    long_term_tasks: List[Task],
) -> None:
    content = []

    content.append(f"[bold]项目名称:[/bold] {project.name}")
    content.append(f"[bold]描述:[/bold] {project.description or '-'}")
    status = "已归档" if project.archived else "进行中"
    status_style = "dim strike" if project.archived else "green"
    content.append(f"[bold]状态:[/bold] [{status_style}]{status}[/]")
    content.append("")

    task_rate = progress.get('task_completion', 0)
    paper_rate = progress.get('paper_progress', 0)
    content.append("[bold]📊 整体进度:[/bold]")
    content.append(f"  任务完成率: [bold]{task_rate:.1f}%[/] "
                   f"({progress.get('done_tasks', 0)}/{progress.get('total_tasks', 0)})")
    content.append(f"  阅读进度: [bold]{paper_rate:.1f}%[/] "
                   f"({progress.get('read_papers', 0)}/{progress.get('total_papers', 0)})")
    content.append(f"  阶段: {progress.get('done_phases', 0)}/{progress.get('total_phases', 0)}")
    content.append(f"  里程碑: {progress.get('done_milestones', 0)}/{progress.get('total_milestones', 0)}")
    content.append("")

    if phases_data:
        content.append("[bold]📋 阶段概览:[/bold]")
        for pd in phases_data:
            phase = pd.get('phase')
            if not phase:
                continue
            phase_status_style = get_phase_status_style(phase.status)
            phase_status_label = get_phase_status_label(phase.status)
            total = pd.get('total', 0)
            done = pd.get('done', 0)
            blocked = pd.get('blocked', 0)
            blocked_tasks = pd.get('blocked_tasks', [])

            content.append(f"  [{phase.order}] [{phase_status_style}]{phase_status_label}[/] "
                           f"[bold]{phase.name}[/]")
            content.append(f"      目标日期: {phase.target_date or '-'} | "
                           f"任务: {done}/{total} | 阻塞: [red]{blocked}[/]")

            if blocked_tasks:
                content.append(f"      [red]阻塞任务:[/]")
                for bt in blocked_tasks[:3]:
                    bt_title = bt.title[:30] + "..." if len(bt.title) > 30 else bt.title
                    content.append(f"        • [{bt.id}] {bt_title}")
                if len(blocked_tasks) > 3:
                    content.append(f"        [dim]...还有 {len(blocked_tasks) - 3} 项[/]")
            content.append("")

    if stagnant_exp:
        content.append("[bold]⏸ 停滞实验:[/bold]")
        for t in stagnant_exp[:5]:
            title_text = t.title[:40] + "..." if len(t.title) > 40 else t.title
            content.append(f"  • [{t.id}] [yellow]{title_text}[/] [dim](更新: {t.updated_at})[/]")
        if len(stagnant_exp) > 5:
            content.append(f"  [dim]...还有 {len(stagnant_exp) - 5} 项[/]")
        content.append("")

    if long_term_tasks:
        content.append("[bold]📅 远期计划:[/bold]")
        for t in long_term_tasks[:5]:
            title_text = t.title[:40] + "..." if len(t.title) > 40 else t.title
            content.append(f"  • [{t.id}] {title_text} [dim](截止: {t.due_date})[/]")
        if len(long_term_tasks) > 5:
            content.append(f"  [dim]...还有 {len(long_term_tasks) - 5} 项[/]")
        content.append("")

    if project.milestones:
        content.append("[bold]🎯 里程碑:[/bold]")
        for m in project.milestones:
            ms_status_style = get_milestone_status_style(m.status)
            ms_status_label = get_milestone_status_label(m.status)
            date_info = m.target_date or "-"
            content.append(f"  • [{ms_status_style}]{ms_status_label}[/] {m.name} "
                           f"[dim](目标: {date_info})[/]")
        content.append("")

    content.append(f"[dim]创建: {project.created_at}[/]")

    console.print(Panel("\n".join(content), title=f"项目复盘 - {project.name}", expand=False))

    if progress.get('total_tasks', 0) > 0:
        progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(bar_width=30),
        )
        with progress_bar:
            task_id = progress_bar.add_task("任务完成进度", total=progress['total_tasks'])
            progress_bar.update(task_id, completed=progress['done_tasks'])


def print_phase_detail(phase_detail_dict: dict) -> None:
    phase = phase_detail_dict.get('phase')
    if not phase:
        print_warning("阶段数据为空")
        return

    content = []
    content.append(f"[bold]阶段名称:[/bold] {phase.name}")
    content.append(f"[bold]描述:[/bold] {phase.description or '-'}")
    status_style = get_phase_status_style(phase.status)
    status_label = get_phase_status_label(phase.status)
    content.append(f"[bold]状态:[/bold] [{status_style}]{status_label}[/]")
    content.append(f"[bold]目标日期:[/bold] {phase.target_date or '-'}")
    content.append(f"[bold]完成日期:[/bold] {phase.done_at or '-'}")
    content.append(f"[bold]顺序:[/bold] {phase.order}")

    done_count = phase_detail_dict.get('done_count', 0)
    blocked_count = phase_detail_dict.get('blocked_count', 0)
    tasks = phase_detail_dict.get('tasks', [])
    total = len(tasks)
    content.append(f"[bold]任务统计:[/bold] 共 {total} 项 | 已完成 {done_count} | 阻塞 [red]{blocked_count}[/]")
    content.append("")
    content.append(f"[dim]创建: {phase.created_at} | 更新: {phase.updated_at}[/]")

    console.print(Panel("\n".join(content), title=f"阶段详情 [{phase.id}]", expand=False))

    blocked_tasks = phase_detail_dict.get('blocked_tasks', [])
    if blocked_tasks:
        print()
        print_tasks(blocked_tasks, title=f"🔴 阻塞任务 ({len(blocked_tasks)})")

    if tasks:
        print()
        print_tasks(tasks, title=f"📋 任务列表 ({len(tasks)})")

    recent_tasks = phase_detail_dict.get('recent_tasks', [])
    if recent_tasks:
        print()
        table = Table(title="🕐 最近更新的任务", show_lines=False)
        table.add_column("ID", style="dim", width=10)
        table.add_column("标题", style="bold", no_wrap=False)
        table.add_column("状态", justify="center", width=10)
        table.add_column("更新时间", style="dim", width=20)

        for t in recent_tasks:
            t_status_style = get_status_style(t.status)
            t_status_label = get_status_label(t.status)
            title_text = t.title[:45] + "..." if len(t.title) > 45 else t.title
            table.add_row(
                t.id,
                title_text,
                Text(t_status_label, style=t_status_style),
                t.updated_at,
            )

        console.print(table)


def print_weekly_reports_list(reports: List[WeeklyReport], project: Optional[str] = None) -> None:
    title = "周报历史记录"
    if project:
        title += f" - {project}"

    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("标题", style="bold", no_wrap=False)
    table.add_column("项目", width=15)
    table.add_column("时间范围", justify="center", width=22)
    table.add_column("详略级别", justify="center", width=10)
    table.add_column("创建时间", style="dim", width=20)

    detail_labels = {
        "simple": "简略",
        "full": "详细",
    }

    for r in reports:
        time_range = f"{r.start_date} ~ {r.end_date}"
        detail_label = detail_labels.get(r.detail_level, r.detail_level)
        title_text = r.title[:30] + "..." if len(r.title) > 30 else r.title

        table.add_row(
            r.id,
            title_text,
            r.project or "-",
            time_range,
            detail_label,
            r.created_at,
        )

    console.print(table)


def print_weekly_report_detail(report: WeeklyReport) -> None:
    content = []
    content.append(f"[bold]标题:[/bold] {report.title}")
    content.append(f"[bold]项目:[/bold] {report.project or '-'}")
    content.append(f"[bold]时间范围:[/bold] {report.start_date} ~ {report.end_date}")

    detail_labels = {
        "simple": "简略",
        "full": "详细",
    }
    detail_label = detail_labels.get(report.detail_level, report.detail_level)
    format_label = report.format.upper()
    content.append(f"[bold]详略级别:[/bold] {detail_label}")
    content.append(f"[bold]格式:[/bold] {format_label}")

    metrics = report.metrics or {}
    if metrics:
        content.append("")
        content.append("[bold]📊 指标摘要:[/bold]")
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                content.append(f"  {key}: [bold]{value}[/]")
            else:
                content.append(f"  {key}: {value}")

    content.append("")
    content.append(f"[dim]创建时间: {report.created_at}[/]")

    console.print(Panel("\n".join(content), title=f"周报详情 [{report.id}]", expand=False))

    if report.content:
        print()
        if report.format == "markdown":
            console.print(Panel(report.content, title="📝 周报内容", expand=False))
        else:
            console.print(Panel(report.content, title="📝 周报内容", expand=False))
