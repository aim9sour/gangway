import time
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from gangway.core.jobs import JobManager


def test_job_manager_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jobs_dir = allowed_root / "jobs"

        jm = JobManager(allowed_root=str(allowed_root), jobs_dir=str(jobs_dir))

        # Start a job that writes to stdout and sleeps
        cmd = "python -u -c \"import time; print('hello from job'); time.sleep(10)\""
        job_id = jm.start_job(cmd, str(allowed_root))
        assert job_id.startswith("job_")

        try:
            # Read status immediately (should be running)
            status = jm.get_job_status(job_id)
            assert status["status"] == "running"
            assert status["pid"] is not None
            assert status.get("create_time") is not None

            # Wait a moment for output and check log
            time.sleep(1.5)
            logs = jm.read_job_logs(job_id, head=10, tail=10)
            assert "hello from job" in logs
        finally:
            # Terminate job
            jm.kill_job(job_id)

        # Verify status updated
        status = jm.get_job_status(job_id)
        assert status["status"] == "killed"


def test_job_manager_nonexistent_job():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jm = JobManager(allowed_root=str(allowed_root))

        with pytest.raises(FileNotFoundError):
            jm.get_job_status("job_nonexistent")

        with pytest.raises(FileNotFoundError):
            jm.kill_job("job_nonexistent")


def test_job_manager_list_jobs():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jobs_dir = allowed_root / "jobs"
        jm = JobManager(allowed_root=str(allowed_root), jobs_dir=str(jobs_dir))

        # Start two quick jobs
        cmd1 = "python -c \"print('job1')\""
        cmd2 = "python -c \"print('job2')\""

        job_id1 = jm.start_job(cmd1, str(allowed_root))
        # sleep slightly to ensure different timestamps/order if needed, though time.time() * 1000 is used
        time.sleep(0.05)
        job_id2 = jm.start_job(cmd2, str(allowed_root))

        jobs = jm.list_jobs()
        assert len(jobs) == 2
        # Should be sorted by start_time (which is in ascending order of creation)
        assert jobs[0]["job_id"] == job_id1
        assert jobs[1]["job_id"] == job_id2

        # Wait for both jobs to finish to release file handles
        for job_id in [job_id1, job_id2]:
            for _ in range(50):
                status = jm.get_job_status(job_id)
                if status["status"] in ("success", "failed"):
                    break
                time.sleep(0.05)


def test_job_manager_failed_startup():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jm = JobManager(allowed_root=str(allowed_root))

        # Start job with non-existent cwd should fail startup
        job_id = jm.start_job(
            "python -c \"print('hi')\"", str(allowed_root / "nonexistent_dir")
        )
        status = jm.get_job_status(job_id)
        assert status["status"] == "failed"
        assert status["pid"] is None
        assert status["exit_code"] == -1
        assert "error" in status


def test_job_manager_path_traversal():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jm = JobManager(allowed_root=str(allowed_root))

        invalid_ids = [
            "../some_job",
            "job_123/../../etc",
            "job_123; rm -rf",
            "job_123.json",
            "job_123.log",
            "job_123\0",
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError):
                jm.get_job_status(invalid_id)

            with pytest.raises(ValueError):
                jm.kill_job(invalid_id)

            with pytest.raises(ValueError):
                jm.read_job_logs(invalid_id)


def test_job_manager_pid_recycling():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jm = JobManager(allowed_root=str(allowed_root))

        # Write metadata for a "running" job with dummy pid and create_time
        job_id = "job_test_recycling"
        meta_file_path = jm.jobs_dir / f"{job_id}.json"
        meta = {
            "job_id": job_id,
            "cmd": "dummy_cmd",
            "pid": 99999,
            "create_time": 123456.78,
            "status": "running",
            "exit_code": None,
            "cwd": str(allowed_root),
            "start_time": "2026-06-26T00:00:00Z",
            "end_time": None,
        }
        jm._atomic_write_json(meta_file_path, meta)

        # Mock psutil.Process to return a different create_time (simulating recycled PID)
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = "running"
        mock_process.create_time.return_value = 123456.78 - 100.0  # different timestamp

        with patch("psutil.Process", return_value=mock_process):
            # Check status: it should reap the job as failed/dead because create_time does not match
            new_status = jm.get_job_status(job_id)
            assert new_status["status"] == "failed"
            assert new_status["exit_code"] == -1

        # Now try to kill the job (should return False and not attempt to kill anything)
        with patch("psutil.Process") as mock_psutil_class:
            mock_psutil_class.return_value = mock_process
            res = jm.kill_job(job_id)
            assert res is False
            mock_process.kill.assert_not_called()


def test_job_manager_unique_ids():
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_root = Path(tmpdir).resolve()
        jm = JobManager(allowed_root=str(allowed_root))

        ids = [jm._generate_job_id() for _ in range(1000)]
        assert len(ids) == len(set(ids))
