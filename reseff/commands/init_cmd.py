"""init 命令 - 初始化工作空间"""
import click
from pathlib import Path

from ..storage import init_storage, is_initialized, get_storage_path
from ..utils.formatting import print_success, print_warning, print_info


@click.command()
@click.option("--force", "-f", is_flag=True, help="强制重新初始化（会覆盖现有数据）")
def init(force: bool):
    """初始化科研效率工具工作空间

    在用户主目录下创建 .reseff 目录用于存储所有数据。
    """
    if is_initialized() and not force:
        print_warning(f"工作空间已存在于 {get_storage_path()}")
        print_info("使用 --force 选项可以重新初始化（会清除所有数据）")
        return

    result = init_storage(force=force)

    if result:
        if force:
            print_success(f"已重新初始化工作空间: {get_storage_path()}")
        else:
            print_success(f"工作空间初始化成功: {get_storage_path()}")
        print_info("现在可以使用 paper add、task add 等命令添加数据了")
    else:
        print_warning("初始化失败")
