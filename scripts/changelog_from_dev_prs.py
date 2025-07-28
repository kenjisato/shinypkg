#!/usr/bin/env python3
import subprocess
import os
import re
import urllib.request
import json
import datetime
import importlib.util
import sys

ABOUT_PATH = "src/shinypkg/__about__.py"
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
BASE_BRANCH = "dev"

# __version__ を取得
spec = importlib.util.spec_from_file_location("about", ABOUT_PATH)
if spec is None or spec.loader is None:
    sys.exit("❌ Failed to load __about__.py")

mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[union-attr]
version = getattr(mod, "__version__", "unknown")

# GitHub PR タイトル取得関数
def get_pr_title(pr_number: str) -> str:
    url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "changelog-script",
        "Accept": "application/vnd.github+json"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.load(res)
            return data.get("title", "")
    except Exception as e:
        print(f"⚠️ Failed to fetch PR #{pr_number}: {e}")
        return ""

# Get the previous tag to determine the range
try:
    # Get the previous tag
    previous_tag = subprocess.check_output(
        ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
        text=True,
    ).strip()
    commit_range = f"{previous_tag}..HEAD"
except subprocess.CalledProcessError:
    # If no previous tag exists, use all commits
    commit_range = "HEAD"

# Get merge commits from the determined range
try:
    log_output = subprocess.check_output(
        ["git", "log", commit_range, "--merges", "--pretty=%s"],
        text=True,
    ).splitlines()
except subprocess.CalledProcessError:
    # Fallback: if the range doesn't work, try to fetch dev branch and use it
    try:
        subprocess.run(["git", "fetch", "origin", "dev:dev"], check=True)
        log_output = subprocess.check_output(
            ["git", "log", f"{BASE_BRANCH}..HEAD", "--merges", "--pretty=%s"],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError:
        # Final fallback: use all merge commits
        log_output = subprocess.check_output(
            ["git", "log", "--merges", "--pretty=%s"],
            text=True,
        ).splitlines()

pattern = re.compile(r"Merge pull request #(\d+)")
pr_titles = []

for line in log_output:
    match = pattern.search(line)
    if match:
        pr_number = match.group(1)
        title = get_pr_title(pr_number)
        if title:
            pr_titles.append(title)

# タイトル分類
sections = {
    "✨ Features": [],
    "🐛 Fixes": [],
    "🧹 Refactoring": [],
    "📝 Documentation": [],
    "🔧 Chores": [],
    "❓ Others": [],
}

prefix_map = {
    "[feat]": "✨ Features",
    "[fix]": "🐛 Fixes",
    "[refactor]": "🧹 Refactoring",
    "[docs]": "📝 Documentation",
    "[chore]": "🔧 Chores",
}

for title in pr_titles:
    matched = False
    for prefix, section in prefix_map.items():
        if title.lower().startswith(prefix):
            sections[section].append(f"- {title}")
            matched = True
            break
    if not matched:
        sections["❓ Others"].append(f"- {title}")

# 変更履歴のテキスト化
today = datetime.date.today().isoformat()
lines = [f"## {today} - {version}", ""]
for section, items in sections.items():
    if items:
        lines.append(f"### {section}")
        lines.extend(items)
        lines.append("")

entry = "\n".join(lines)

# CHANGELOG.md に追記
try:
    with open("CHANGELOG.md", "a", encoding="utf-8") as f:
        f.write(entry + "\n")
except FileNotFoundError:
    # Create CHANGELOG.md if it doesn't exist
    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write("# Changelog\n\n")
        f.write(entry + "\n")

# GitHub Release 作成
tag = f"v{version}"
try:
    subprocess.run([
        "gh", "release", "create", tag,
        "--title", f"Release {tag}",
        "--notes", entry,
        "--target", "main"
    ], check=True)
    print(f"✅ Created GitHub release {tag}")
except subprocess.CalledProcessError as e:
    # If release already exists, try to update it
    try:
        subprocess.run([
            "gh", "release", "edit", tag,
            "--title", f"Release {tag}",
            "--notes", entry
        ], check=True)
        print(f"✅ Updated existing GitHub release {tag}")
    except subprocess.CalledProcessError:
        print(f"⚠️ Failed to create or update GitHub release {tag}: {e}")
        # Don't fail the entire workflow if release creation fails
