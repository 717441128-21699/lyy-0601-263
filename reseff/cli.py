"""ResEff CLI - 科研助理个人效率工具"""
import click
from typing import Optional
from rich.console import Console

from . import __version__
from .storage import load_db, search_all
from .utils.formatting import print_search_results, print_error, print_warning
from .commands.init_cmd import init
from .commands.paper_cmd import paper
from .commands.note_cmd import note
from .commands.task_cmd import task
from .commands.plan_cmd import plan
from .commands.review_cmd import review
from .commands.export_cmd import export

console = Console()


@click.group(
    help="""
ResEff - 科研助理个人效率命令行工具

用于集中管理论文阅读、实验安排和待办事项。

\b
命令组:
  init    初始化工作空间
  paper   文献管理
  note    笔记管理
  task    任务管理
  plan    计划与安排（含阶段/里程碑）
  review  回顾与统计
  export  导出与归档
  search  综合搜索（文献/笔记/任务）

使用 'reseff <command> --help' 查看各命令的详细帮助。
""",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    __version__,
    "-V", "--version",
    message="%(prog)s v%(version)s - 科研助理个人效率工具"
)
def cli():
    """ResEff CLI 主入口"""
    pass


@cli.command("search")
@click.argument("keyword")
@click.option("--project", "-p", default=None, help="按项目筛选")
def search_cmd(keyword: str, project: Optional[str]):
    """综合搜索：在文献、笔记、任务中搜索关键词

    KEYWORD: 搜索关键词
    """
    try:
        db = load_db()
    except FileNotFoundError as e:
        print_error(str(e))
        return

    results = search_all(db, keyword, project=project)
    total = len(results["papers"]) + len(results["notes"]) + len(results["tasks"])

    if total == 0:
        hint = f" in project '{project}'" if project else ""
        print_warning(f"未找到包含 '{keyword}' 的内容{hint}")
        return

    print_search_results(results)


cli.add_command(init)
cli.add_command(paper)
cli.add_command(note)
cli.add_command(task)
cli.add_command(plan)
cli.add_command(review)
cli.add_command(export)


def main():
    """程序入口函数"""
    try:
        cli()
    except click.Abort:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
