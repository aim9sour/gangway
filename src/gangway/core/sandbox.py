import os
from pathlib import Path
from typing import Optional

def verify_path(path_str: str, allowed_root: Optional[str]) -> str:
    """Verify that a path is within the allowed root directory, if specified.
    
    If allowed_root is None, returns the absolute path.
    Otherwise, resolves the target path and allowed root absolutely, and checks
    if the target path resides inside the allowed root. Raises PermissionError if not.
    """
    if not allowed_root:
        return os.path.abspath(path_str)
        
    allowed_path = Path(allowed_root).resolve()
    target_path = Path(path_str).resolve()
    
    try:
        target_path.relative_to(allowed_path)
    except ValueError:
        if target_path != allowed_path:
            raise PermissionError(
                f"Access Denied: Path '{path_str}' lies outside allowed root '{allowed_root}'"
            )
            
    return str(target_path)
