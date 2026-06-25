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
        sm = StateManager(allowed_root=str(allowed_root), state_file_path=str(state_file))
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
        
        sm = StateManager(allowed_root=str(allowed_root), state_file_path=str(state_file))
        assert Path(sm.get_cwd()) == allowed_root

def test_state_manager_outside_allowed_root_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        state_file = allowed_root / ".gangway_state.json"
        
        # Write a path outside allowed_root to the state file
        outside_path = allowed_root.parent / "outside"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"cwd": str(outside_path)}, f)
            
        sm = StateManager(allowed_root=str(allowed_root), state_file_path=str(state_file))
        assert Path(sm.get_cwd()) == allowed_root

