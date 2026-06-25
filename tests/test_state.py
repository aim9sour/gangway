import os
import json
import tempfile
import pytest
from pathlib import Path
from gangway.core.state import StateManager


def test_state_manager_behavior():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        state_file = allowed_root / ".gangway_state.json"

        # Initialize
        sm = StateManager(
            allowed_root=str(allowed_root), state_file_path=str(state_file)
        )
        assert Path(sm.get_cwd()) == allowed_root

        # Change directory (relative)
        sub_dir = allowed_root / "subdir"
        sub_dir.mkdir()
        sm.set_cwd("subdir")
        assert Path(sm.get_cwd()) == sub_dir

        # Verify state file persistence
        assert state_file.exists()
        with open(state_file, "r") as f:
            data = json.load(f)
            assert data["cwd"] == str(sub_dir)

        # Resolve path relative to current CWD
        res = sm.resolve_path("file.txt")
        assert Path(res) == sub_dir / "file.txt"

        # Sandboxing check outside allowed_root
        with pytest.raises(PermissionError):
            sm.set_cwd("../../outside")


def test_state_manager_corrupted_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        state_file = allowed_root / ".gangway_state.json"

        # Write corrupted JSON to the state file
        state_file.write_text("invalid json", encoding="utf-8")

        sm = StateManager(
            allowed_root=str(allowed_root), state_file_path=str(state_file)
        )
        assert Path(sm.get_cwd()) == allowed_root


def test_state_manager_outside_allowed_root_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        state_file = allowed_root / ".gangway_state.json"

        # Write a path outside allowed_root to the state file
        outside_path = allowed_root.parent / "outside"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cwd": str(outside_path)}, f)

        sm = StateManager(
            allowed_root=str(allowed_root), state_file_path=str(state_file)
        )
        assert Path(sm.get_cwd()) == allowed_root


def test_state_manager_no_allowed_root():
    with (
        tempfile.TemporaryDirectory() as tmpdir1,
        tempfile.TemporaryDirectory() as tmpdir2,
    ):
        dir1 = Path(tmpdir1).resolve()
        dir2 = Path(tmpdir2).resolve()
        state_file = dir1 / ".gangway_state.json"

        # Initialize with allowed_root=None
        sm = StateManager(allowed_root=None, state_file_path=str(state_file))

        # Verify initial cwd is os.getcwd() resolved
        assert Path(sm.get_cwd()) == Path(os.getcwd()).resolve()

        # We can change to dir2 even if it's completely unrelated (no allowed_root restriction)
        sm.set_cwd(str(dir2))
        assert Path(sm.get_cwd()) == dir2

        # Verify resolution
        res = sm.resolve_path("sub/file.txt")
        assert Path(res) == dir2 / "sub" / "file.txt"


def test_state_manager_set_cwd_not_a_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        state_file = allowed_root / ".gangway_state.json"

        sm = StateManager(
            allowed_root=str(allowed_root), state_file_path=str(state_file)
        )

        # Target a file
        test_file = allowed_root / "test_file.txt"
        test_file.write_text("hello", encoding="utf-8")

        with pytest.raises(NotADirectoryError):
            sm.set_cwd(str(test_file))

        # Target a non-existent path
        non_existent = allowed_root / "non_existent_folder"
        with pytest.raises(NotADirectoryError):
            sm.set_cwd(str(non_existent))
