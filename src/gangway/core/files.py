import os
import glob
import base64
import shutil
import zipfile
import tarfile
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
        results.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else None,
                "modified": stat.st_mtime,
            }
        )
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


def preview_file(
    path_str: str, allowed_root: Optional[str], head: int = 80, tail: int = 40
) -> str:
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

    divider = (
        f"\n[... OMITTED {omitted_lines} LINES (Approx: {omitted_bytes} bytes) ...]\n"
    )
    return head_content + divider + tail_content


def project_overview(path_str: str, allowed_root: Optional[str]) -> Dict[str, Any]:
    target = verify_path(path_str, allowed_root)
    overview: Dict[str, Any] = {"files": [], "readme_content": "", "recent_files": []}

    # 1. Walk to map structure (max depth 3)
    target_path = Path(target)
    for root, dirs, files in os.walk(target):
        depth = len(Path(root).relative_to(target_path).parts)
        if depth > 2:
            dirs.clear()  # don't descend further
            continue
        for file in files:
            full_path = os.path.join(root, file)
            # ignore venv and git
            if (
                ".git" in full_path
                or ".venv" in full_path
                or "__pycache__" in full_path
            ):
                continue
            overview["files"].append(os.path.relpath(full_path, target))

    # 2. Get readme content
    for ext in ["README.md", "README.txt", "README"]:
        readme_path = os.path.join(target, ext)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                    overview["readme_content"] = f.read(2000)  # limit to first 2kb
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
    overview["recent_files"] = [
        os.path.relpath(x[0], target) for x in all_files_stat[:10]
    ]

    return overview


def upload_chunk(
    file_path: str,
    chunk_index: int,
    total_chunks: int,
    data_b64: str,
    allowed_root: Optional[str],
) -> bool:
    target = verify_path(file_path, allowed_root)

    # Store in a temporary folder
    temp_dir = os.path.join(os.path.dirname(target), ".gangway_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    chunk_file = os.path.join(
        temp_dir, f"{os.path.basename(target)}.part_{chunk_index}"
    )
    with open(chunk_file, "w", encoding="utf-8") as f:
        f.write(data_b64)
    return True


def assemble_upload(
    file_path: str, total_chunks: int, allowed_root: Optional[str]
) -> str:
    target = verify_path(file_path, allowed_root)
    temp_dir = os.path.join(os.path.dirname(target), ".gangway_uploads")

    # Read and concatenate
    chunks = []
    for idx in range(total_chunks):
        part_path = os.path.join(temp_dir, f"{os.path.basename(target)}.part_{idx}")
        if not os.path.exists(part_path):
            raise FileNotFoundError(f"Missing chunk index {idx} at '{part_path}'")
        with open(part_path, "r", encoding="utf-8") as infile:
            chunks.append(infile.read())
        os.remove(part_path)

    # Decode and write
    full_data = base64.b64decode("".join(chunks))
    with open(target, "wb") as outfile:
        outfile.write(full_data)

    # Clean up directory if empty
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

    return target


def download_chunk(
    file_path: str, chunk_index: int, chunk_size: int, allowed_root: Optional[str]
) -> Dict[str, Any]:
    target = verify_path(file_path, allowed_root)
    if not os.path.exists(target):
        raise FileNotFoundError(f"File not found: '{file_path}'")

    file_size = os.path.getsize(target)
    offset = chunk_index * chunk_size

    if offset >= file_size:
        return {"chunk_index": chunk_index, "data_b64": "", "has_more": False}

    with open(target, "rb") as f:
        f.seek(offset)
        data = f.read(chunk_size)

    has_more = (offset + len(data)) < file_size
    return {
        "chunk_index": chunk_index,
        "data_b64": base64.b64encode(data).decode("utf-8"),
        "has_more": has_more,
    }


def compress_archive(
    archive_path: str, source_dir: str, allowed_root: Optional[str], format: str = "zip"
) -> str:
    target_archive = verify_path(archive_path, allowed_root)
    target_source = verify_path(source_dir, allowed_root)

    fmt_lower = format.lower()
    if fmt_lower == "zip":
        base_name = (
            target_archive[:-4]
            if target_archive.lower().endswith(".zip")
            else target_archive
        )
        actual_path = shutil.make_archive(base_name, "zip", target_source)
    elif fmt_lower in ("tar.gz", "tgz", "gztar"):
        if target_archive.lower().endswith(".tar.gz"):
            base_name = target_archive[:-7]
        elif target_archive.lower().endswith(".tgz"):
            base_name = target_archive[:-4]
        else:
            base_name = target_archive
        actual_path = shutil.make_archive(base_name, "gztar", target_source)
    else:
        raise ValueError("Unsupported archive format. Choose 'zip' or 'tar.gz'.")

    return actual_path


def extract_archive(
    archive_path: str, extract_dir: str, allowed_root: Optional[str]
) -> str:
    target_archive = verify_path(archive_path, allowed_root)
    target_extract = verify_path(extract_dir, allowed_root)

    os.makedirs(target_extract, exist_ok=True)

    if target_archive.lower().endswith(".zip"):
        with zipfile.ZipFile(target_archive, "r") as zip_ref:
            # security path traversal check for zip entries
            for member in zip_ref.namelist():
                member_path = os.path.join(target_extract, member)
                verify_path(member_path, allowed_root)
            zip_ref.extractall(target_extract)
    elif target_archive.lower().endswith((".tar.gz", ".tgz")):
        with tarfile.open(target_archive, "r:gz") as tar_ref:
            for member in tar_ref.getmembers():
                member_path = os.path.join(target_extract, member.name)
                verify_path(member_path, allowed_root)
            tar_ref.extractall(target_extract)
    else:
        raise ValueError(
            "Unsupported archive format for extraction. Use .zip or .tar.gz / .tgz"
        )

    return target_extract
