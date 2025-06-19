# _git.py

import subprocess
from pathlib import Path


def is_git_repo(path: Path) -> bool:
    try:
        # Git ワークツリー内かどうか確認
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        inside_work_tree = result.stdout.strip() == "true"

        # さらに `.git` ディレクトリの内部ではないことも確認
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], cwd=path, text=True
        ).strip()

        # `.git` の内部なら、それは対象外にする
        git_dir_abs = (path / git_dir).resolve()
        path_abs = path.resolve()
        is_inside_git_dir = git_dir_abs in path_abs.parents or git_dir_abs == path_abs

        return inside_work_tree and not is_inside_git_dir

    except subprocess.CalledProcessError:
        return False


def get_git_author_info() -> dict:
    def get_config_value(key: str) -> str:
        try:
            return subprocess.check_output(
                ["git", "config", "--get", key], text=True
            ).strip()
        except subprocess.CalledProcessError:
            return ""

    return {
        "author_name": get_config_value("user.name") or "Your Name",
        "author_email": get_config_value("user.email") or "you@example.com",
    }
