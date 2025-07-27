import os
from pathlib import Path

from typer.testing import CliRunner

from shinypkg.cli import app


runner = CliRunner()


def test_cli_help():
    """Test that CLI help works"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Packaging a shiny app made easy" in result.stdout


def test_create_command_help():
    """Test that create command help works"""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "Initialize a Shiny app project" in result.stdout


def test_pack_command_help():
    """Test that pack command help works"""
    result = runner.invoke(app, ["pack", "--help"])
    assert result.exit_code == 0
    assert "Convert a flat Shiny app project into an installable package" in result.stdout


def test_upgrade_command_help():
    """Test that upgrade command help works"""
    result = runner.invoke(app, ["upgrade", "--help"])
    assert result.exit_code == 0
    assert "Upgrade a generated file from the template" in result.stdout


def test_create_basic_project(tmp_path):
    """Test creating a basic project"""
    project_name = "testapp"
    
    # Change to tmp_path to create project there
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, [
            "create", 
            project_name,
            "--author-name", "Test Author",
            "--author-email", "test@example.com"
        ])
        
        assert result.exit_code == 0
        assert "Initialized Shiny project" in result.stdout
        
        # Check that project structure was created
        project_path = tmp_path / project_name
        package_path = project_path / project_name
        
        assert project_path.exists()
        assert package_path.exists()
        assert (package_path / "app.py").exists()
        assert (package_path / "_util.py").exists()
        assert (package_path / "__init__.py").exists()
        assert (package_path / "__main__.py").exists()
        assert (project_path / "pyproject.toml").exists()
        assert (project_path / "README.md").exists()
        assert (project_path / ".gitignore").exists()
        
        # Check pyproject.toml content
        pyproject_content = (project_path / "pyproject.toml").read_text()
        assert "Test Author" in pyproject_content
        assert "test@example.com" in pyproject_content
        assert f'name = "{project_name}"' in pyproject_content
        
    finally:
        os.chdir(original_cwd)


def test_create_project_no_app(tmp_path):
    """Test creating a project without sample app files"""
    project_name = "testapp"
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, [
            "create", 
            project_name,
            "--no-app",
            "--author-name", "Test Author",
            "--author-email", "test@example.com"
        ])
        
        assert result.exit_code == 0
        assert "Skipping sample code generation" in result.stdout
        
        project_path = tmp_path / project_name
        package_path = project_path / project_name
        
        # Should not have app.py and _util.py
        assert not (package_path / "app.py").exists()
        assert not (package_path / "_util.py").exists()
        
        # Should still have other files
        assert (package_path / "__init__.py").exists()
        assert (package_path / "__main__.py").exists()
        assert (project_path / "pyproject.toml").exists()
        
    finally:
        os.chdir(original_cwd)


def test_create_project_existing_directory(tmp_path):
    """Test that create fails when directory already exists"""
    project_name = "testapp"
    project_path = tmp_path / project_name
    package_path = project_path / project_name
    
    # Create the package directory first
    package_path.mkdir(parents=True)
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, [
            "create", 
            project_name,
            "--author-name", "Test Author",
            "--author-email", "test@example.com"
        ])
        
        assert result.exit_code == 1
        assert "already exists" in result.stdout
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_basic(tmp_path):
    """Test basic pack command functionality"""
    # Create a source app
    source = tmp_path / "myapp"
    source.mkdir()
    (source / "app.py").write_text("# app.py")
    (source / "requirements.txt").write_text("flask==2.0.0\nrequests>=2.25.0")
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["pack", "myapp"])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        assert "Found requirements.txt" in result.stdout
        assert "uv add -r" in result.stdout
        assert "To run the app:" in result.stdout
        
        # Check that packaged structure was created
        target = tmp_path / "myapp-packaged"
        package_dir = target / "myapp"
        
        assert target.exists()
        assert package_dir.exists()
        assert (package_dir / "app.py").exists()
        assert (package_dir / "requirements.txt").exists()
        assert (package_dir / "__init__.py").exists()
        assert (package_dir / "__main__.py").exists()
        assert (target / "pyproject.toml").exists()
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_no_requirements(tmp_path):
    """Test pack command with no requirements.txt"""
    # Create a source app without requirements.txt
    source = tmp_path / "myapp"
    source.mkdir()
    (source / "app.py").write_text("# app.py")
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["pack", "myapp"])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        assert "No requirements.txt found" in result.stdout
        assert "uv add shiny" in result.stdout
        assert "To run the app:" in result.stdout
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_inplace(tmp_path):
    """Test pack command with --inplace option"""
    # Create a source app
    source = tmp_path / "myapp"
    source.mkdir()
    (source / "app.py").write_text("# app.py")
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["pack", "myapp", "--inplace"])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        
        # Check that files were moved within the same directory
        package_dir = source / "myapp"
        assert package_dir.exists()
        assert (package_dir / "app.py").exists()
        assert (package_dir / "__init__.py").exists()
        assert (source / "pyproject.toml").exists()
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_nonexistent_source(tmp_path):
    """Test pack command with non-existent source"""
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["pack", "nonexistent"])
        
        assert result.exit_code == 1
        assert "Source directory does not exist" in result.stdout
        
    finally:
        os.chdir(original_cwd)


def test_upgrade_command_nonexistent_file(tmp_path):
    """Test upgrade command with non-existent file"""
    # Create a basic project structure without the target file
    project_path = tmp_path / "testproject"
    project_path.mkdir()
    
    original_cwd = Path.cwd()
    try:
        os.chdir(project_path)
        
        result = runner.invoke(app, ["upgrade", "__main__.py"])
        
        assert result.exit_code == 1
        assert "not" in result.stdout.lower() and "found" in result.stdout.lower()
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_target_outside_current_directory(tmp_path):
    """Test pack command with target outside current directory shows correct path"""
    # Create source app in a subdirectory
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "app.py").write_text("# app.py")
    (source_dir / "requirements.txt").write_text("flask==2.0.0")
    
    # Create a different directory to run the command from
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    
    # Specify target in yet another location
    target_dir = tmp_path / "output" / "myapp-packaged"
    
    original_cwd = Path.cwd()
    try:
        os.chdir(work_dir)
        
        result = runner.invoke(app, ["pack", str(source_dir), str(target_dir)])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        assert "Found requirements.txt" in result.stdout
        
        # Should show absolute path since target is not relative to current directory
        # Check that the target directory path appears in cd command
        assert "cd " in result.stdout
        # Check that it's an absolute path (contains parts of the tmp_path)
        # Remove newlines and spaces to handle formatting
        stdout_clean = result.stdout.replace('\n', ' ').replace('  ', ' ')
        assert "output/myapp-packaged" in stdout_clean
        
        # Verify the target was created correctly
        assert target_dir.exists()
        package_dir = target_dir / "source"
        assert package_dir.exists()
        assert (package_dir / "app.py").exists()
        assert (package_dir / "requirements.txt").exists()
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_target_relative_to_current_directory(tmp_path):
    """Test pack command with target relative to current directory shows relative path"""
    # Create source app
    source_dir = tmp_path / "myapp"
    source_dir.mkdir()
    (source_dir / "app.py").write_text("# app.py")
    
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["pack", "myapp"])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        
        # Should show relative path since target is relative to current directory
        assert "cd myapp-packaged" in result.stdout
        # Should not show absolute path
        assert str(tmp_path) not in result.stdout.split("cd ")[1].split("\n")[0]
        
    finally:
        os.chdir(original_cwd)


def test_pack_command_inplace_no_cd_needed(tmp_path):
    """Test pack command with inplace option shows no cd instruction"""
    # Create source app
    source_dir = tmp_path / "myapp"
    source_dir.mkdir()
    (source_dir / "app.py").write_text("# app.py")
    
    original_cwd = Path.cwd()
    try:
        os.chdir(source_dir)
        
        result = runner.invoke(app, ["pack", ".", "--inplace"])
        
        assert result.exit_code == 0
        assert "Packaging complete" in result.stdout
        
        # Should not show any cd instruction since we're already in the target
        lines_with_cd = [line for line in result.stdout.split('\n') if 'cd ' in line]
        assert len(lines_with_cd) == 0
        
    finally:
        os.chdir(original_cwd)
