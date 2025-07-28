from pathlib import Path
import fnmatch
import shutil
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional

from rich.console import Console
from ._template import render_template
from ._git import get_git_author_info

console = Console()

EXCLUDED_PATTERNS = [
    "README.md",
    "LICENSE",
    ".gitignore",
]

def _is_excluded(file: str) -> bool:
    return any(fnmatch.fnmatch(file, pat) for pat in EXCLUDED_PATTERNS)


@contextmanager
def _backup_and_rollback(source: Path, target: Path, inplace: bool) -> Generator[None, None, None]:
    """
    Create a backup and provide rollback functionality if the operation fails.
    """
    backup_dir: Optional[Path] = None
    temp_dir_obj = None
    target_existed = target.exists() if not inplace else False
    
    try:
        if inplace:
            # For inplace operations, create a backup of the source
            temp_dir_obj = tempfile.TemporaryDirectory()
            backup_dir = Path(temp_dir_obj.name) / "backup"
            console.print("[dim]Creating backup for rollback...[/dim]")
            shutil.copytree(source, backup_dir)
            
        yield
        
        # If we reach here, operation was successful
        if inplace:
            console.print("[dim]Operation successful, removing backup.[/dim]")
            
    except Exception as e:
        console.print(f"[red]Operation failed: {e}[/red]")
        console.print("[yellow]Rolling back changes...[/yellow]")
        
        if inplace and backup_dir and backup_dir.exists():
            # Restore from backup
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(backup_dir, target)
            console.print("[green]Successfully restored from backup.[/green]")
        elif not inplace:
            # Remove the target directory if it was created
            if target.exists() and not target_existed:
                shutil.rmtree(target)
                console.print("[green]Successfully removed incomplete target directory.[/green]")
        
        # Re-raise the original exception
        raise
    finally:
        # Clean up temporary directory
        if temp_dir_obj:
            temp_dir_obj.cleanup()

def pack_app(source: Path, target: Path, inplace: bool = False):
    source = source.resolve()
    target = target.resolve()

    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")
  
    if not inplace:
        if target.exists():
            raise FileExistsError(f"Target directory {target} already exists.")
    else:
        if target != source:
            raise ValueError("If inplace=True, source and target must be the same.")
    
    # Use backup and rollback context manager
    with _backup_and_rollback(source, target, inplace):
        # Initial setup
        if not inplace:
            shutil.copytree(source, target)
        
        project_name = source.name
        package_name = project_name.replace("-", "_")
        package_dir = target / package_name
        package_dir.mkdir(exist_ok=True)

        # Move files into the package dir
        for path in target.iterdir():
            if path == package_dir:
                continue
            if path.is_file() and _is_excluded(path.name):
                continue
            shutil.move(path, package_dir / path.name)
            console.log(f"Moved: {path} -> {package_dir / path.name}")

        # context for templates
        git_info = get_git_author_info()
        context = {
            "project_name": project_name,
            "package_name": package_name,
            "author_name": git_info["author_name"],
            "author_email": git_info["author_email"],
        }

        # Generate template files
        (package_dir / "__init__.py").write_text(
            render_template("__init__.py.j2", context), encoding="utf-8"
        )
        (package_dir / "__main__.py").write_text(
            render_template("__main__.py.j2", context), encoding="utf-8"
        )
        (target / "pyproject.toml").write_text(
            render_template("pyproject.toml.j2", context), encoding="utf-8"
        )

        # Check for requirements.txt and return whether it exists
        requirements_file = package_dir / "requirements.txt"
        return requirements_file.exists()
