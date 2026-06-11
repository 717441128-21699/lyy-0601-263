"""paper 命令 - 文献管理"""
import click
from typing import Optional

from ..models import Paper, Project, _now_str
from ..storage import (
    load_db, add_paper, get_paper, update_paper, delete_paper,
    list_papers, search_papers, get_project, add_project,
    get_paper_notes, get_paper_tasks, ensure_project,
)
from ..utils.formatting import (
    print_papers, print_paper_detail, print_success, print_error,
    print_warning, get_status_label,
)


@click.group()
def paper():
    """文献管理命令

    用于添加、查看、编辑和管理科研文献。
    """
    pass


@paper.command()
@click.option("--title", "-t", required=True, help="文献标题")
@click.option("--authors", "-a", default="", help="作者列表")
@click.option("--year", "-y", type=int, default=None, help="发表年份")
@click.option("--venue", "-v", default="", help="期刊/会议名称")
@click.option("--url", "-u", default="", help="文献链接")
@click.option("--summary", "-s", default="", help="文献摘要")
@click.option("--status", default="unread",
              type=click.Choice(["unread", "reading", "read", "skipped"]),
              help="阅读状态")
@click.option("--project", "-p", default="", help="所属项目")
@click.option("--tag", multiple=True, help="标签（可多次指定）")
def add(title: str, authors: str, year: Optional[int], venue: str,
        url: str, summary: str, status: str, project: str, tag):
    """添加新文献"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    if project and not get_project(db, project):
        ensure_project(db, project)
        print_success(f"已自动创建新项目: {project}")

    tags = list(tag)
    paper = Paper(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        url=url,
        status=status,
        summary=summary,
        project=project,
        tags=tags,
    )

    if status == "read":
        paper.read_at = _now_str()

    add_paper(db, paper)
    print_success(f"文献添加成功: [{paper.id}] {paper.title}")


@paper.command(name="list")
@click.option("--project", "-p", default=None, help="按项目筛选")
@click.option("--status", "-s", default=None,
              type=click.Choice(["unread", "reading", "read", "skipped"]),
              help="按状态筛选")
def list_cmd(project: Optional[str], status: Optional[str]):
    """列出所有文献"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    papers = list_papers(db, project=project, status=status)

    if not papers:
        print_warning("暂无文献记录")
        return

    title = "文献列表"
    if project:
        title += f" - 项目: {project}"
    if status:
        title += f" - 状态: {get_status_label(status)}"

    print_papers(papers, title=title)


@paper.command()
@click.argument("id")
def show(id: str):
    """查看文献详情"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    notes = get_paper_notes(db, id)
    tasks = get_paper_tasks(db, id)
    print_paper_detail(paper, notes=notes, tasks=tasks)


@paper.command()
@click.argument("id")
@click.option("--status", "-s",
              type=click.Choice(["unread", "reading", "read", "skipped"]),
              help="设置阅读状态")
@click.option("--summary", default=None, help="更新摘要")
@click.option("--project", default=None, help="更新项目")
@click.option("--tag", multiple=True, help="添加标签（可多次指定）")
def update(id: str, status: Optional[str], summary: Optional[str],
           project: Optional[str], tag):
    """更新文献信息"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    kwargs = {}
    if status is not None:
        kwargs["status"] = status
        if status == "read" and not paper.read_at:
            kwargs["read_at"] = _now_str()
    if summary is not None:
        kwargs["summary"] = summary
    if project is not None:
        kwargs["project"] = project
        if project and not get_project(db, project):
            ensure_project(db, project)
            print_success(f"已自动创建新项目: {project}")
    if tag:
        new_tags = list(set(paper.tags + list(tag)))
        kwargs["tags"] = new_tags

    if not kwargs:
        print_warning("未指定任何更新内容")
        return

    updated = update_paper(db, id, **kwargs)
    if updated:
        print_success(f"文献更新成功: [{id}]")


@paper.command(name="status")
@click.argument("id")
@click.argument("new_status",
                type=click.Choice(["unread", "reading", "read", "skipped"]))
def set_status(id: str, new_status: str):
    """快速标记阅读状态

    NEW_STATUS: unread|reading|read|skipped
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    kwargs = {"status": new_status}
    if new_status == "read" and not paper.read_at:
        kwargs["read_at"] = _now_str()

    update_paper(db, id, **kwargs)
    print_success(f"文献状态已更新为: {get_status_label(new_status)}")


@paper.command()
@click.argument("id")
@click.argument("summary_text", required=False)
@click.option("--file", "-f", type=click.Path(exists=True),
              help="从文件读取摘要内容")
def summary(id: str, summary_text: Optional[str], file: Optional[str]):
    """记录文献摘要

    可以直接提供摘要文本，或使用 --file 从文件读取。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    content = ""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
    elif summary_text:
        content = summary_text
    else:
        print_warning("请提供摘要文本或使用 --file 指定文件")
        return

    update_paper(db, id, summary=content)
    print_success("摘要已更新")


@paper.command(name="add-step")
@click.argument("id")
@click.argument("step")
def add_experiment_step(id: str, step: str):
    """关联实验步骤到文献

    将从文献中得到的实验方法记录为步骤。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    new_steps = paper.experiment_steps + [step]
    update_paper(db, id, experiment_steps=new_steps)
    print_success(f"实验步骤已添加，当前共 {len(new_steps)} 个步骤")


@paper.command(name="remove-step")
@click.argument("id")
@click.argument("index", type=int)
def remove_experiment_step(id: str, index: int):
    """删除文献关联的实验步骤

    INDEX: 步骤序号（从1开始）
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    if index < 1 or index > len(paper.experiment_steps):
        print_error(f"步骤序号无效，有效范围: 1-{len(paper.experiment_steps)}")
        return

    removed = paper.experiment_steps.pop(index - 1)
    update_paper(db, id, experiment_steps=paper.experiment_steps)
    print_success(f"已删除步骤: {removed}")


@paper.command()
@click.argument("keyword")
def search(keyword: str):
    """搜索文献

    在标题、作者、摘要和标签中搜索关键词。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    results = search_papers(db, keyword)

    if not results:
        print_warning(f"未找到包含 '{keyword}' 的文献")
        return

    print_papers(results, title=f"搜索结果: '{keyword}' ({len(results)} 条)")


@paper.command()
@click.argument("id")
@click.option("--yes", is_flag=True, help="确认删除，无需提示")
def delete(id: str, yes: bool):
    """删除文献"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper = get_paper(db, id)
    if not paper:
        print_error(f"未找到 ID 为 {id} 的文献")
        return

    if not yes:
        click.confirm(f"确定要删除文献 '{paper.title}' 吗?", abort=True)

    delete_paper(db, id)
    print_success(f"文献已删除: [{id}]")
