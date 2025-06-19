# cli.py

import difflib
import subprocess
from pathlib import Path
from typing import Annotated


import typer
from rich.console import Console

from shinypkg._git import is_git_repo, get_git_author_info
from shinypkg._template import render_template

app = typer.Typer()
console = Console()


@app.callback()
def callback():
    """
    Packaging a shiny app made easy
    """


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Project name.")] = ".",
    author_name: Annotated[
        str, typer.Option(help="Author name", show_default=False)
    ] = "",
    author_email: Annotated[
        str, typer.Option(help="Author email", show_default=False)
    ] = "",
):
    """
    Initialize a Shiny app project.
    """
    # Step 1: Normalize project name and paths
    project_path = Path(name).resolve()
    package_name = project_path.name.replace("-", "_")
    package_path = project_path / package_name

    if package_path.exists():
        console.print(f"[red]Error:[/red] Directory '{package_path}' already exists.")
        raise typer.Exit(1)

    # Step 2: Git fallback
    git_info = get_git_author_info()

    # Step 3: CLI argument, git info then default
    context = {
        "package_name": package_name,
        "project_name": project_path.name,
        "author_name": author_name or git_info["author_name"],
        "author_email": author_email or git_info["author_email"],
    }

    # Step 4: Create directory structure
    package_path.mkdir(parents=True)

    # Step 5: Create files from templates
    (package_path / "app.py").write_text(
        render_template("app.py.j2", context), encoding="utf-8"
    )
    (package_path / "_util.py").write_text(
        render_template("_util.py.j2", context), encoding="utf-8"
    )
    (package_path / "__init__.py").write_text(
        render_template("__init__.py.j2", context), encoding="utf-8"
    )
    (package_path / "__main__.py").write_text(
        render_template("__main__.py.j2", context), encoding="utf-8"
    )
    (project_path / "pyproject.toml").write_text(
        render_template("pyproject.toml.j2", context), encoding="utf-8"
    )
    (project_path / "README.md").write_text(
        render_template("README.md.j2", context), encoding="utf-8"
    )
    (project_path / ".gitignore").write_text(
        render_template(".gitignore.j2", context), encoding="utf-8"
    )

    # Step 6: Run git init
    if not is_git_repo(project_path):
        try:
            subprocess.run(
                ["git", "init"], cwd=project_path, check=True, stdout=subprocess.DEVNULL
            )
            console.print("[green]Initialized empty Git repository.[/green]")
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not initialize Git repository: {e}"
            )
    else:
        console.print("[dim]Git repository already exists, skipping `git init`.[/dim]")

    # Final message
    console.print(f"[green]Initialized Shiny project at:[/green] {project_path}")
    console.print("\nTo run:")
    console.print(f"  cd {project_path.name}")
    console.print("  uv add shiny")
    console.print()
    console.print(f"  .... edit { package_name }/app.py ....")
    console.print()
    console.print(f"  uv run {project_path.name}")


@app.command()
def upgrade(
    filename: Annotated[
        str, typer.Argument(help="File to upgrade (e.g. __main__.py)")
    ] = "__main__.py",
    force: Annotated[bool, typer.Option(help="Overwrite without confirmation")] = False,
    output: Annotated[
        Path | None,
        typer.Option(help="Write the updated file to this path instead of overwriting"),
    ] = None,
):
    """
    Upgrade a generated file from the template.
    """
    project_path = Path(".").resolve()
    package_name = project_path.name.replace("-", "_")
    target_path = project_path / package_name / filename

    if not target_path.exists():
        console.print(f"[red]Error:[/red] File '{target_path}' not found.")
        raise typer.Exit(1)

    template_name = filename + ".j2"

    try:
        with target_path.open("r", encoding="utf-8") as f:
            current_content = f.read()
    except Exception as e:
        console.print(f"[red]Error reading {target_path}:[/red] {e}")
        raise typer.Exit(1)

    rendered_content = render_template(
        template_name,
        {
            "package_name": package_name,
            "project_name": project_path.name,
            "author_name": "Unknown",
            "author_email": "unknown@example.com",
        },
    )

    diff = list(
        difflib.unified_diff(
            current_content.splitlines(),
            rendered_content.splitlines(),
            fromfile=str(target_path),
            tofile=f"{filename} (template)",
            lineterm="",
        )
    )

    if not diff:
        console.print(f"[green]{filename} is already up-to-date.[/green]")
        return

    console.print(f"[yellow]Differences detected in {filename}:[/yellow]\n")
    console.print("\n".join(diff))

    if output:
        try:
            output.write_text(rendered_content, encoding="utf-8")
            console.print(f"[green]Rendered updated template to:[/green] {output}")
        except Exception as e:
            console.print(f"[red]Error writing to '{output}':[/red] {e}")
    elif force or typer.confirm(
        "Do you want to overwrite this file with the updated template?"
    ):
        target_path.write_text(rendered_content, encoding="utf-8")
        console.print(f"[green]Updated '{filename}' with template version.[/green]")
    else:
        console.print(f"[dim]Skipped overwriting '{filename}'.[/dim]")
