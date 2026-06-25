import os
import glob
from pathlib import Path
from typing import Optional, List, Dict, Any
from gangway.core.sandbox import verify_path

def list_directory(path_str: str, allowed_root: Optional[str]) -> List[Dict[str, Any]]:
    target = verify_path(path_str, allowed_root)
    results = []
    if not os.path.isdir(target):
        raise NotADirectoryError(f"'{path_str}' is not a directory")
        
    for entry in os.scandir(target):
        stat = entry.stat()
        results.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": stat.st_size if entry.is_file() else None,
            "modified": stat.st_mtime
        })
    return results

def glob_search(pattern: str, allowed_root: Optional[str]) -> List[str]:
    # We must ensure that target glob does not escape allowed root
    # A simple way is to run glob and then filter the results using verify_path
    results = []
    # If the pattern is relative, run it in the current directory or allowed_root
    base_dir = allowed_root if allowed_root else os.getcwd()
    search_pattern = os.path.join(base_dir, pattern)
    
    for filepath in glob.glob(search_pattern, recursive=True):
        try:
            verified = verify_path(filepath, allowed_root)
            results.append(verified)
        except PermissionError:
            pass
    return results

def preview_file(path_str: str, allowed_root: Optional[str], head: int = 80, tail: int = 40) -> str:
    target = verify_path(path_str, allowed_root)
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    if total_lines <= (head + tail):
        return "".join(lines)
        
    head_content = "".join(lines[:head])
    tail_content = "".join(lines[-tail:])
    
    file_stat = os.stat(target)
    # Estimate size omitted
    head_bytes = len(head_content.encode("utf-8", errors="replace"))
    tail_bytes = len(tail_content.encode("utf-8", errors="replace"))
    omitted_bytes = max(0, file_stat.st_size - head_bytes - tail_bytes)
    
    omitted_lines = total_lines - head - tail
    
    divider = f"\n[... OMITTED {omitted_lines} LINES (Approx: {omitted_bytes} bytes) ...]\n"
    return head_content + divider + tail_content

def project_overview(path_str: str, allowed_root: Optional[str]) -> Dict[str, Any]:
    target = verify_path(path_str, allowed_root)
    overview: Dict[str, Any] = {"files": [], "readme_content": "", "recent_files": []}
    
    # 1. Walk to map structure (max depth 3)
    target_path = Path(target)
    for root, dirs, files in os.walk(target):
        depth = len(Path(root).relative_to(target_path).parts)
        if depth > 2:
            dirs.clear() # don't descend further
            continue
        for file in files:
            full_path = os.path.join(root, file)
            # ignore venv and git
            if ".git" in full_path or ".venv" in full_path or "__pycache__" in full_path:
                continue
            overview["files"].append(os.path.relpath(full_path, target))
            
    # 2. Get readme content
    for ext in ["README.md", "README.txt", "README"]:
        readme_path = os.path.join(target, ext)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                    overview["readme_content"] = f.read(2000) # limit to first 2kb
                break
            except Exception:
                pass
                
    # 3. Get recent files
    all_files_stat = []
    for root, _, files in os.walk(target):
        if ".git" in root or ".venv" in root or "__pycache__" in root:
            continue
        for file in files:
            full_path = os.path.join(root, file)
            try:
                stat = os.stat(full_path)
                all_files_stat.append((full_path, stat.st_mtime))
            except Exception:
                pass
    all_files_stat.sort(key=lambda x: x[1], reverse=True)
    overview["recent_files"] = [os.path.relpath(x[0], target) for x in all_files_stat[:10]]
    
    return overview
