"""输出格式化工具"""
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from ..models import Paper, Note, Task, Project

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


def print_paper_detail(paper: Paper) -> None:
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


def print_task_detail(task: Task) -> None:
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
