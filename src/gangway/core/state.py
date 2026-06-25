import os
import json
from pathlib import Path
from typing import Optional
from gangway.core.sandbox import verify_path

class StateManager:
    def __init__(self, allowed_root: Optional[str] = None, state_file_path: Optional[str] = None):
        self.allowed_root = Path(allowed_root).resolve() if allowed_root else None
        
        if state_file_path:
            self.state_file = Path(state_file_path)
        elif self.allowed_root:
            self.state_file = self.allowed_root / ".gangway_state.json"
        else:
            self.state_file = Path(os.getcwd()) / ".gangway_state.json"
            
        self._current_cwd = self._load_state()

    def _load_state(self) -> Path:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_path = Path(data.get("cwd", ""))
                    if self.allowed_root:
                        verify_path(str(saved_path), str(self.allowed_root))
                    return saved_path.resolve()
            except Exception:
                pass
        return self.allowed_root if self.allowed_root else Path(os.getcwd()).resolve()

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"cwd": str(self._current_cwd)}, f, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass

    def get_cwd(self) -> str:
        return str(self._current_cwd)

    def set_cwd(self, path_str: str) -> str:
        target_path = Path(path_str)
        if not target_path.is_absolute():
            target_path = self._current_cwd / target_path
            
        resolved_path = Path(verify_path(str(target_path), str(self.allowed_root) if self.allowed_root else None))
        
        if not resolved_path.is_dir():
            raise NotADirectoryError(f"'{path_str}' is not a directory")
            
        self._current_cwd = resolved_path
        self._save_state()
        return str(self._current_cwd)

    def resolve_path(self, path_str: str) -> str:
        target_path = Path(path_str)
        if not target_path.is_absolute():
            target_path = self._current_cwd / target_path
        return verify_path(str(target_path), str(self.allowed_root) if self.allowed_root else None)
