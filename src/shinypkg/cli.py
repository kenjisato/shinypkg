# cli.py

import difflib
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from ._git import is_git_repo, get_git_author_info
from ._template import render_template
from ._pack import pack_app

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
    no_app: Annotated[
        bool,
        typer.Option(
            "--no-app",
            help="Do not create app.py or _util.py",
        )
    ] = False,
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
    if no_app:
        console.print("[yellow]Skipping sample code generation.[/yellow]")
    else:
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


@app.command()
def pack(
    source: Annotated[
        Path, typer.Argument(help="Directory of existing Shiny app")
    ],
    target: Annotated[
        Optional[Path],
        typer.Argument(help="Target directory for packaged app", show_default=False)
    ] = None,
    inplace: Annotated[
        bool,
        typer.Option("--inplace", help="Modify the source directory in-place"),
    ] = False,
):
    """
    Convert a flat Shiny app project into an installable package.
    """

    source = source.resolve()

    if not source.exists():
        console.print("[red]Error:[/red] Source directory does not exist.")
        raise typer.Exit(1)

    if target is None:
        if inplace:
            target = source
        else:
            target = source.parent / f"{source.name}-packaged"
    else:
        target = target.resolve()

    if not inplace and target.exists():
        console.print(f"[red]Error:[/red] Target directory {target} already exists.")
        raise typer.Exit(1)

    console.print(f"[blue]Packaging:[/blue] {source}")
    if not inplace:
        console.print(f"[green]Output will be written to:[/green] {target}")

    try:
        has_requirements = pack_app(source, target, inplace=inplace)
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        raise typer.Exit(1)

    console.print("[green]✔ Packaging complete.[/green]")
    
    # Check if we need to cd into the target directory
    current_dir = Path.cwd()
    need_cd = current_dir != target
    
    # Calculate the path to target directory
    target_path_str = ""
    if need_cd:
        try:
            # Try to get relative path first (cleaner output)
            target_path_str = str(target.relative_to(current_dir))
        except ValueError:
            # If relative path fails, use absolute path
            target_path_str = str(target)
    
    # Check for requirements.txt and provide installation instructions
    project_name = source.name
    package_name = project_name.replace("-", "_")
    
    if has_requirements:
        relative_path = f"{package_name}/requirements.txt"
        console.print("\n[blue]Found requirements.txt in the package.[/blue]")
        console.print("To install dependencies, run:")
        
        if need_cd:
            console.print(f"  [green]cd {target_path_str}[/green]")
            console.print(f"  [green]uv add -r {relative_path}[/green]")
        else:
            console.print(f"  [green]uv add -r {relative_path}[/green]")
            
        console.print("\nAlternatively:")
        if need_cd:
            console.print(f"  [dim]cd {target_path_str} && pip install -r {relative_path}[/dim]")
        else:
            console.print(f"  [dim]pip install -r {relative_path}[/dim]")
    else:
        console.print("\n[dim]No requirements.txt found. You may need to manually install dependencies:[/dim]")
        
        if need_cd:
            console.print(f"  [dim]cd {target_path_str}[/dim]")
            console.print("  [dim]uv add shiny  # or other dependencies[/dim]")
        else:
            console.print("  [dim]uv add shiny  # or other dependencies[/dim]")
    
    # Show how to run the app after installation
    console.print("\nTo run the app:")
    console.print(f"  [green]uv run {project_name}[/green]")
    console.print("\nAlternatively:")
    console.print(f"  [dim]python -m {package_name}[/dim]")
