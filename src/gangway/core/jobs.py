import os
import sys
import json
import time
import subprocess
import uuid
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import psutil


class JobManager:
    _active_processes: Dict[str, subprocess.Popen] = {}

    def __init__(
        self, allowed_root: Optional[str] = None, jobs_dir: Optional[str] = None
    ):
        self.allowed_root = Path(allowed_root).resolve() if allowed_root else None

        if jobs_dir:
            self.jobs_dir = Path(jobs_dir)
        elif self.allowed_root:
            self.jobs_dir = self.allowed_root / ".gangway_jobs"
        else:
            self.jobs_dir = Path(os.getcwd()) / ".gangway_jobs"

        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_json(self, file_path: Path, data: Dict[str, Any]):
        temp_file = file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, file_path)
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise e

    def _generate_job_id(self) -> str:
        return f"job_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    def _validate_job_id(self, job_id: str) -> None:
        if not isinstance(job_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", job_id):
            raise ValueError(f"Invalid job ID: {job_id}")

    def start_job(self, cmd: str, cwd: str) -> str:
        job_id = self._generate_job_id()
        log_file_path = self.jobs_dir / f"{job_id}.log"
        meta_file_path = self.jobs_dir / f"{job_id}.json"

        log_file = open(log_file_path, "wb")

        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=(sys.platform != "win32")
            )
            self._active_processes[job_id] = proc
            try:
                p = psutil.Process(proc.pid)
                create_time = p.create_time()
            except Exception:
                create_time = None
        except Exception as e:
            log_file.close()
            meta = {
                "job_id": job_id,
                "cmd": cmd,
                "pid": None,
                "create_time": None,
                "status": "failed",
                "exit_code": -1,
                "cwd": cwd,
                "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": str(e),
            }
            self._atomic_write_json(meta_file_path, meta)
            return job_id

        log_file.close()

        meta = {
            "job_id": job_id,
            "cmd": cmd,
            "pid": proc.pid,
            "create_time": create_time,
            "status": "running",
            "exit_code": None,
            "cwd": cwd,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "end_time": None,
        }
        self._atomic_write_json(meta_file_path, meta)
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        self._validate_job_id(job_id)
        meta_file_path = self.jobs_dir / f"{job_id}.json"
        if not meta_file_path.exists():
            raise FileNotFoundError(f"Job '{job_id}' not found")

        with open(meta_file_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if meta["status"] == "running":
            # First, check if we have the active Popen object in this session
            proc = self._active_processes.get(job_id)
            if proc is not None:
                exit_code = proc.poll()
                if exit_code is not None:
                    meta["status"] = "success" if exit_code == 0 else "failed"
                    meta["exit_code"] = exit_code
                    meta["end_time"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    )
                    self._atomic_write_json(meta_file_path, meta)
                    self._active_processes.pop(job_id, None)
                    return meta

            # Fallback to checking PID status
            pid = meta["pid"]
            alive = False
            is_recycled = False
            if pid is not None:
                try:
                    p = psutil.Process(pid)
                    if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                        stored_create_time = meta.get("create_time")
                        if stored_create_time is not None:
                            if p.create_time() == stored_create_time:
                                alive = True
                            else:
                                is_recycled = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if not alive:
                exit_code = -1
                if pid is not None and not is_recycled:
                    if sys.platform != "win32":
                        try:
                            res = os.waitpid(pid, os.WNOHANG)
                            if res[0] != 0:
                                status_code = res[1]
                                exit_code = (
                                    os.WEXITSTATUS(status_code)
                                    if os.WIFEXITED(status_code)
                                    else -1
                                )
                        except Exception:
                            pass
                    # If we don't have waitpid on Windows, we default to exit_code = -1 if alive was False

                meta["status"] = "success" if exit_code == 0 else "failed"
                meta["exit_code"] = exit_code
                meta["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._atomic_write_json(meta_file_path, meta)
                self._active_processes.pop(job_id, None)

        return meta

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        for file in self.jobs_dir.glob("job_*.json"):
            job_id = file.stem
            try:
                status = self.get_job_status(job_id)
                jobs.append(status)
            except Exception:
                pass
        jobs.sort(key=lambda x: x["start_time"])
        return jobs

    def kill_job(self, job_id: str) -> bool:
        self._validate_job_id(job_id)
        meta = self.get_job_status(job_id)
        if meta["status"] != "running":
            return False

        pid = meta["pid"]
        if pid is not None:
            try:
                parent = psutil.Process(pid)
                stored_create_time = meta.get("create_time")
                if stored_create_time is not None and parent.create_time() == stored_create_time:
                    try:
                        procs = parent.children(recursive=True)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        procs = []
                    # Kill children first, then parent
                    for child in procs:
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    try:
                        parent.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        meta["status"] = "killed"
        meta["exit_code"] = -9
        meta["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._atomic_write_json(self.jobs_dir / f"{job_id}.json", meta)

        self._active_processes.pop(job_id, None)
        return True

    def read_job_logs(self, job_id: str, head: int = 100, tail: int = 100) -> str:
        self._validate_job_id(job_id)
        log_file_path = self.jobs_dir / f"{job_id}.log"
        if not log_file_path.exists():
            return "[No logs found for this job]"

        from gangway.core.files import preview_file

        return preview_file(
            str(log_file_path), str(self.jobs_dir), head=head, tail=tail
        )
