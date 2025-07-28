#!/usr/bin/env python3
import subprocess
import importlib.util
import sys
import datetime

ABOUT_PATH = "src/shinypkg/__about__.py"

# バージョン取得
spec = importlib.util.spec_from_file_location("about", ABOUT_PATH)
if spec is None or spec.loader is None:
    print(f"❌ Could not load spec from {ABOUT_PATH}", file=sys.stderr)
    sys.exit(1)

mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[union-attr]

version = getattr(mod, "__version__", None)
if version is None:
    print(f"❌ __version__ not found", file=sys.stderr)
    sys.exit(1)

# 最新タグの取得
try:
    last_tag = subprocess.check_output(
        ["git", "describe", "--tags", "--abbrev=0"],
        text=True,
    ).strip()
except subprocess.CalledProcessError:
    last_tag = None

# PR タイトルのみ取得
log_range = f"{last_tag}..HEAD" if last_tag else ""
log_output = subprocess.check_output(
    ["git", "log", "--merges", "--pretty=format:%s", log_range],
    text=True,
).strip()

# フィルタして PR タイトルだけ抜き出す
lines = []
for line in log_output.splitlines():
    if line.startswith("Merge pull request"):
        # Merge pull request #42 from user/feature-title
        # ...
        lines.append(f"- {line}")

# CHANGELOG に追記
date_str = datetime.date.today().isoformat()
changelog_entry = f"## {date_str} - {version}\n\n" + "\n".join(lines) + "\n\n"

with open("CHANGELOG.md", "a", encoding="utf-8") as f:
    f.write(changelog_entry)

# GitHub Release 作成（gh CLI）
release_title = f"Release v{version}"
gh_cmd = [
    "gh", "release", "create", f"v{version}",
    "--title", release_title,
    "--notes", changelog_entry,
    "--target", "main"
]

subprocess.run(gh_cmd, check=True)
