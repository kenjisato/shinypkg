from pathlib import Path

import pytest

from shinypkg._pack import pack_app, _is_excluded


def create_dummy_app(path: Path, files: list[str]):
    path.mkdir(parents=True, exist_ok=True)
    for file in files:
        (path / file).write_text(f"# {file}", encoding="utf-8")

@pytest.mark.parametrize(
    "tree", [
    ["app.py", "_util.py"],
    ["app-test.py", "foo.py", "README.md"],
])
@pytest.mark.parametrize("inplace", [False, True])
def test_pack_into_new_directory(tmp_path, inplace, tree):
    """
    Ensure that pack_app correctly moves files to a package directory,
    creating the appropriate package structure and excluding EXCLUDED files.
    """
    source = tmp_path / "myapp"
    create_dummy_app(source, tree)

    target = source if inplace else tmp_path / "myapp-packaged"

    pack_app(source, target, inplace=inplace)

    project_name = source.name
    package_name = project_name.replace("-", "_")
    package_dir = target / package_name

    for item in tree:
        if _is_excluded(item):
            assert (target / item).exists()
        else:
            assert (package_dir / item).exists()
            
    assert (package_dir / "__main__.py").exists()
    assert (package_dir / "__init__.py").exists()
    assert (target / "pyproject.toml").exists()


def test_pack_raises_on_existing_target(tmp_path):
    source = tmp_path / "app"
    target = tmp_path / "existing"
    source.mkdir()
    target.mkdir()
    create_dummy_app(source, ["app.py", "_util.py"])

    with pytest.raises(FileExistsError):
        pack_app(source, target, inplace=False)


def test_pack_with_requirements_txt(tmp_path):
    """Test that pack_app correctly handles requirements.txt"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py", "requirements.txt"])
    
    target = tmp_path / "myapp-packaged"
    
    # Should return True when requirements.txt exists
    has_requirements = pack_app(source, target, inplace=False)
    assert has_requirements is True
    
    # requirements.txt should be moved to package directory
    package_dir = target / "myapp"
    assert (package_dir / "requirements.txt").exists()
    assert not (target / "requirements.txt").exists()


def test_pack_without_requirements_txt(tmp_path):
    """Test that pack_app correctly handles absence of requirements.txt"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py", "_util.py"])
    
    target = tmp_path / "myapp-packaged"
    
    # Should return False when requirements.txt doesn't exist
    has_requirements = pack_app(source, target, inplace=False)
    assert has_requirements is False


def test_pack_raises_on_nonexistent_source(tmp_path):
    """Test that pack_app raises FileNotFoundError for non-existent source"""
    source = tmp_path / "nonexistent"
    target = tmp_path / "target"
    
    with pytest.raises(FileNotFoundError):
        pack_app(source, target, inplace=False)


def test_pack_inplace_validation(tmp_path):
    """Test that pack_app validates inplace parameter correctly"""
    source = tmp_path / "myapp"
    target = tmp_path / "different"
    create_dummy_app(source, ["app.py"])
    
    with pytest.raises(ValueError, match="If inplace=True, source and target must be the same."):
        pack_app(source, target, inplace=True)


def test_excluded_files_handling(tmp_path):
    """Test that excluded files are handled correctly"""
    source = tmp_path / "myapp"
    excluded_files = ["README.md", "LICENSE", ".gitignore"]
    regular_files = ["app.py", "_util.py"]
    all_files = excluded_files + regular_files
    
    create_dummy_app(source, all_files)
    target = tmp_path / "myapp-packaged"
    
    pack_app(source, target, inplace=False)
    
    package_dir = target / "myapp"
    
    # Excluded files should remain at top level
    for excluded_file in excluded_files:
        assert (target / excluded_file).exists()
        assert not (package_dir / excluded_file).exists()
    
    # Regular files should be moved to package directory
    for regular_file in regular_files:
        assert (package_dir / regular_file).exists()
        assert not (target / regular_file).exists()


def test_project_name_with_hyphens(tmp_path):
    """Test that project names with hyphens are handled correctly"""
    source = tmp_path / "my-app-name"
    create_dummy_app(source, ["app.py"])
    
    target = tmp_path / "my-app-name-packaged"
    
    pack_app(source, target, inplace=False)
    
    # Package directory should use underscores
    package_dir = target / "my_app_name"
    assert package_dir.exists()
    assert (package_dir / "app.py").exists()
    assert (package_dir / "__init__.py").exists()
    assert (package_dir / "__main__.py").exists()


def test_pack_rollback_on_template_error(tmp_path):
    """Test that pack_app rolls back when template rendering fails"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py"])
    
    target = tmp_path / "myapp-packaged"
    
    # Mock render_template to raise an exception
    from unittest.mock import patch
    
    with patch('shinypkg._pack.render_template', side_effect=Exception("Template error")):
        with pytest.raises(Exception, match="Template error"):
            pack_app(source, target, inplace=False)
    
    # Target directory should not exist after rollback
    assert not target.exists()


def test_pack_rollback_inplace_on_error(tmp_path):
    """Test that pack_app rolls back inplace operations when they fail"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py", "data.txt"])
    
    # Create a backup of original content for verification
    original_files = list(source.iterdir())
    original_content = {}
    for file in original_files:
        if file.is_file():
            original_content[file.name] = file.read_text()
    
    # Mock render_template to raise an exception after some processing
    from unittest.mock import patch
    
    with patch('shinypkg._pack.render_template', side_effect=Exception("Template error")):
        with pytest.raises(Exception, match="Template error"):
            pack_app(source, source, inplace=True)
    
    # Source should be restored to original state
    restored_files = list(source.iterdir())
    assert len(restored_files) == len(original_files)
    
    # Check that original files are restored
    for file in restored_files:
        if file.is_file() and file.name in original_content:
            assert file.read_text() == original_content[file.name]


def test_pack_rollback_preserves_existing_target(tmp_path):
    """Test that rollback doesn't remove pre-existing target directories"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py"])
    
    target = tmp_path / "existing-target"
    target.mkdir()
    (target / "existing-file.txt").write_text("existing content")
    
    # This should fail because target already exists
    with pytest.raises(FileExistsError):
        pack_app(source, target, inplace=False)
    
    # Target should still exist with original content
    assert target.exists()
    assert (target / "existing-file.txt").exists()
    assert (target / "existing-file.txt").read_text() == "existing content"


def test_pack_successful_operation_no_rollback_messages(tmp_path, capsys):
    """Test that successful operations don't show rollback messages"""
    source = tmp_path / "myapp"
    create_dummy_app(source, ["app.py"])
    
    target = tmp_path / "myapp-packaged"
    
    pack_app(source, target, inplace=False)
    
    # Capture output
    captured = capsys.readouterr()
    
    # Should not contain rollback-related messages
    assert "Rolling back" not in captured.out
    assert "Operation failed" not in captured.out
    assert "restored from backup" not in captured.out
