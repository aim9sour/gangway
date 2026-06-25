# Fix Task 3: Background Job Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement fixes for Background Job Manager including ID collision prevention, create_time recording, PID recycling prevention, and path traversal validation.

**Architecture:**
- Import `uuid` and `re` in `jobs.py`.
- Append a 6-character UUID prefix/suffix to the job ID.
- Retrieve process `create_time` on startup and save it to metadata JSON.
- Verify process `create_time` matches the metadata when checking status/killing.
- Use regex validation on job ID inputs to prevent path traversal.
- Add robust unit tests.

**Tech Stack:** Python, psutil, pytest, uuid, re

## Global Constraints
- Target files: `src/gangway/core/jobs.py`, `tests/test_jobs.py`
- All tests must pass with 0 lint errors.

---

### Task 1: Update Job ID Generation & Input Validation

**Files:**
- Modify: `src/gangway/core/jobs.py`

**Interfaces:**
- Consumes: None
- Produces: Sanitized inputs and unique job IDs.

- [ ] **Step 1: Update Imports, generate_job_id, and validate_job_id**
  Add imports and rewrite `_generate_job_id` and add `_validate_job_id` helper:
  ```python
  import uuid
  import re
  
  def _generate_job_id(self) -> str:
      return f"job_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

  def _validate_job_id(self, job_id: str) -> None:
      if not isinstance(job_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", job_id):
          raise ValueError(f"Invalid job ID: {job_id}")
  ```

- [ ] **Step 2: Add validation calls**
  Call `_validate_job_id` at the start of:
  - `get_job_status(self, job_id: str)`
  - `kill_job(self, job_id: str)`
  - `read_job_logs(self, job_id: str, head: int = 100, tail: int = 100)`

---

### Task 2: Implement create_time Logging and Verification

**Files:**
- Modify: `src/gangway/core/jobs.py`

**Interfaces:**
- Consumes: UUIDs and validated IDs.
- Produces: Safe checking and termination of processes.

- [ ] **Step 1: Save process create_time in start_job**
  Update `start_job` to query and save `create_time` in metadata JSON.
  ```python
  # After subprocess.Popen succeeds:
  try:
      p = psutil.Process(proc.pid)
      create_time = p.create_time()
  except Exception:
      create_time = None
  ```

- [ ] **Step 2: Verify create_time in get_job_status**
  Update `get_job_status` to only mark process as alive if `p.create_time() == stored_create_time`.
  Also skip `os.waitpid` if the PID is recycled.

- [ ] **Step 3: Verify create_time in kill_job**
  Update `kill_job` to only kill the process tree if `parent.create_time() == stored_create_time`.

---

### Task 3: Implement Unit Tests and Verify

**Files:**
- Modify: `tests/test_jobs.py`

- [ ] **Step 1: Add unit tests**
  Add tests for:
  - Job ID uniqueness in rapid succession.
  - Path traversal validation checking `ValueError`.
  - PID recycling mocking `psutil.Process` to return a different `create_time`.

- [ ] **Step 2: Run tests and ensure clean exit**
  Run `uv run pytest tests/test_jobs.py` and check results.
  Run `uv run ruff check` to ensure zero lints.
