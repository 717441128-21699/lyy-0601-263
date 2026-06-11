"""note 命令 - 笔记管理"""
import click
from typing import Optional

from ..models import Note
from ..storage import (
    load_db, add_note, get_note, update_note, delete_note,
    list_notes, search_notes, get_paper,
)
from ..utils.formatting import (
    print_notes, print_note_detail, print_success, print_error,
    print_warning,
)


@click.group()
def note():
    """笔记管理命令

    用于记录阅读笔记、实验心得和想法。
    """
    pass


@note.command()
@click.option("--content", "-c", required=True, help="笔记内容")
@click.option("--paper", "-p", default=None, help="关联的文献ID")
@click.option("--project", "-j", default="", help="所属项目")
@click.option("--tag", multiple=True, help="标签（可多次指定）")
def add(content: str, paper: Optional[str], project: str, tag):
    """添加新笔记"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    paper_title = ""
    if paper:
        p = get_paper(db, paper)
        if not p:
            print_error(f"未找到 ID 为 {paper} 的文献")
            return
        paper_title = p.title

    tags = list(tag)
    note = Note(
        content=content,
        paper_id=paper,
        paper_title=paper_title,
        project=project,
        tags=tags,
    )

    add_note(db, note)
    print_success(f"笔记添加成功: [{note.id}]")


@note.command(name="list")
@click.option("--paper", "-p", default=None, help="按文献ID筛选")
@click.option("--project", "-j", default=None, help="按项目筛选")
def list_cmd(paper: Optional[str], project: Optional[str]):
    """列出所有笔记"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    notes = list_notes(db, paper_id=paper, project=project)

    if not notes:
        print_warning("暂无笔记记录")
        return

    title = "笔记列表"
    if paper:
        p = get_paper(db, paper)
        if p:
            title += f" - 文献: {p.title[:30]}..."
        else:
            title += f" - 文献ID: {paper}"
    if project:
        title += f" - 项目: {project}"

    print_notes(notes, title=title)


@note.command()
@click.argument("id")
def show(id: str):
    """查看笔记详情"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    note = get_note(db, id)
    if not note:
        print_error(f"未找到 ID 为 {id} 的笔记")
        return

    print_note_detail(note)


@note.command()
@click.argument("id")
@click.option("--content", "-c", default=None, help="更新笔记内容")
@click.option("--project", "-j", default=None, help="更新项目")
@click.option("--tag", multiple=True, help="添加标签（可多次指定）")
def update(id: str, content: Optional[str], project: Optional[str], tag):
    """更新笔记信息"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    note = get_note(db, id)
    if not note:
        print_error(f"未找到 ID 为 {id} 的笔记")
        return

    kwargs = {}
    if content is not None:
        kwargs["content"] = content
    if project is not None:
        kwargs["project"] = project
    if tag:
        new_tags = list(set(note.tags + list(tag)))
        kwargs["tags"] = new_tags

    if not kwargs:
        print_warning("未指定任何更新内容")
        return

    updated = update_note(db, id, **kwargs)
    if updated:
        print_success(f"笔记更新成功: [{id}]")


@note.command()
@click.argument("keyword")
def search(keyword: str):
    """搜索笔记

    在笔记内容和标签中搜索关键词。
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    results = search_notes(db, keyword)

    if not results:
        print_warning(f"未找到包含 '{keyword}' 的笔记")
        return

    print_notes(results, title=f"搜索结果: '{keyword}' ({len(results)} 条)")


@note.command()
@click.argument("id")
@click.option("--yes", is_flag=True, help="确认删除，无需提示")
def delete(id: str, yes: bool):
    """删除笔记"""
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    note = get_note(db, id)
    if not note:
        print_error(f"未找到 ID 为 {id} 的笔记")
        return

    if not yes:
        preview = note.content[:50] + "..." if len(note.content) > 50 else note.content
        click.confirm(f"确定要删除笔记 '{preview}' 吗?", abort=True)

    delete_note(db, id)
    print_success(f"笔记已删除: [{id}]")
