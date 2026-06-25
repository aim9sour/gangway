import tempfile
import os
import pytest
from gangway.core.files import list_directory, glob_search, preview_file, project_overview

def test_list_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file and a subdirectory
        file_path = os.path.join(tmpdir, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("content")
        
        subdir_path = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir_path, exist_ok=True)
        
        # Test listing directory
        entries = list_directory(tmpdir, tmpdir)
        assert len(entries) == 2
        
        file_entry = next(e for e in entries if e["name"] == "test_file.txt")
        assert file_entry["is_dir"] is False
        assert file_entry["size"] == 7
        assert "modified" in file_entry
        
        subdir_entry = next(e for e in entries if e["name"] == "subdir")
        assert subdir_entry["is_dir"] is True
        assert subdir_entry["size"] is None
        
        # Test listing non-directory
        with pytest.raises(NotADirectoryError):
            list_directory(file_path, tmpdir)
            
        # Test sandboxing
        outside_path = os.path.join(tmpdir, "..")
        with pytest.raises(PermissionError):
            list_directory(outside_path, tmpdir)


def test_glob_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files
        file1 = os.path.join(tmpdir, "a.py")
        file2 = os.path.join(tmpdir, "b.txt")
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir, exist_ok=True)
        file3 = os.path.join(subdir, "c.py")
        
        for fpath in [file1, file2, file3]:
            with open(fpath, "w") as f:
                f.write("dummy")
                
        # Search for .py files
        py_files = glob_search("**/*.py", tmpdir)
        assert len(py_files) == 2
        # Verify paths are returned (may be resolved or not depending on implementation, but must end with appropriate subpaths)
        assert any(f.endswith("a.py") for f in py_files)
        assert any(f.endswith("c.py") for f in py_files)
        
        # Search with pattern that tries to go outside allowed_root
        # Should not include files from outside allowed_root
        results = glob_search("../**/*", subdir)
        # Results should only contain files within subdir, even if glob matched parent files
        assert all(f.startswith(subdir) for f in results)


def test_preview_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Test small file (no omission)
        small_file = os.path.join(tmpdir, "small.txt")
        with open(small_file, "w") as f:
            f.write("line 1\nline 2")
            
        preview = preview_file(small_file, tmpdir, head=5, tail=5)
        assert preview == "line 1\nline 2"
        
        # 2. Test large file (omission)
        large_file = os.path.join(tmpdir, "large.txt")
        lines = [f"Line {i}\n" for i in range(200)]
        with open(large_file, "w") as f:
            f.writelines(lines)
            
        preview = preview_file(large_file, tmpdir, head=10, tail=5)
        assert "Line 0" in preview
        assert "Line 9" in preview
        assert "OMITTED" in preview
        assert "Line 199" in preview
        assert "Line 10\n" not in preview
        
        # 3. Test sandboxing
        outside_file = os.path.join(tmpdir, "..", "outside.txt")
        with pytest.raises(PermissionError):
            preview_file(outside_file, tmpdir)


def test_project_overview():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create readme
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write("Project Readme info")
            
        # Create git and venv directories to ensure they are ignored
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir, exist_ok=True)
        with open(os.path.join(git_dir, "config"), "w") as f:
            f.write("git config")
            
        venv_dir = os.path.join(tmpdir, ".venv")
        os.makedirs(venv_dir, exist_ok=True)
        with open(os.path.join(venv_dir, "pip.conf"), "w") as f:
            f.write("pip config")
            
        # Create some project files
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir, exist_ok=True)
        main_py = os.path.join(src_dir, "main.py")
        with open(main_py, "w") as f:
            f.write("print('hello')")
            
        nested_dir = os.path.join(src_dir, "utils", "helpers")
        os.makedirs(nested_dir, exist_ok=True)
        helper_py = os.path.join(nested_dir, "helper.py")
        with open(helper_py, "w") as f:
            f.write("def help(): pass")
            
        # Verify overview
        overview = project_overview(tmpdir, tmpdir)
        
        # Files should contain README.md and src/main.py
        # But should NOT contain .git/config, .venv/pip.conf
        assert "README.md" in overview["files"]
        assert os.path.join("src", "main.py").replace("\\", "/") in [f.replace("\\", "/") for f in overview["files"]]
        assert not any(".git" in f or ".venv" in f for f in overview["files"])
        
        # Walk depth limit: since depth limit is 3 (max depth 3 - wait, let's check:
        # os.walk depth check: Target depth is 0, src depth is 1, utils depth is 2, helpers depth is 3.
        # "depth > 2: dirs.clear() # don't descend further"
        # So it descends into src, and then under src it has dirs like utils. 
        # For utils, depth is 2. So it lists utils files, but does not descend into helpers.
        # Thus helper_py (depth 3) should NOT be in overview["files"]
        assert os.path.join("src", "utils", "helpers", "helper.py").replace("\\", "/") not in [f.replace("\\", "/") for f in overview["files"]]
        
        # Readme content
        assert overview["readme_content"] == "Project Readme info"
        
        # Recent files
        assert "README.md" in overview["recent_files"]
        assert os.path.join("src", "main.py").replace("\\", "/") in [f.replace("\\", "/") for f in overview["recent_files"]]
        
        # Test sandboxing
        outside_path = os.path.join(tmpdir, "..")
        with pytest.raises(PermissionError):
            project_overview(outside_path, tmpdir)
