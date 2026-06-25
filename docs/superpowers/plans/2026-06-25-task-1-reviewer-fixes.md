# Task 1 Reviewer Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve reviewer findings for Task 1 by updating path resolution, TOML loading, and port casting in the configuration module.

**Architecture:** 
1. Use `pathlib.Path.resolve()` to resolve `allowed_root` to an absolute path when it is specified in `load_config`.
2. Refactor configuration file loading to open files within the format-specific blocks (JSON/TOML) so the file is not opened twice.
3. Wrap all port casting with try-except blocks to catch invalid integers and raise descriptive `ValueError` exceptions.

**Tech Stack:** Python 3, `pytest`

## Global Constraints

- Run all commands inside the workspace: `C:\Users\abdo\.gemini\antigravity\scratch\gangway`
- Verify tests pass before moving on.

---

### Task 1: Path Resolution for `allowed_root`

**Files:**
- Modify: `src/gangway/core/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: Existing `load_config` API
- Produces: `load_config` resolving `allowed_root` to its absolute path using `pathlib.Path.resolve()`

- [ ] **Step 1: Write a test for `allowed_root` path resolution**
  
  Add `test_load_config_allowed_root_resolution` to `tests/test_config.py`.
  ```python
  def test_load_config_allowed_root_resolution():
      # Test relative path resolution
      relative_path = "./some_rel_path"
      cfg = load_config(allowed_root=relative_path)
      from pathlib import Path
      expected = str(Path(relative_path).resolve())
      assert cfg.allowed_root == expected
  ```

- [ ] **Step 2: Run test to verify it fails**
  
  Run: `uv run pytest tests/test_config.py -k test_load_config_allowed_root_resolution`
  Expected: FAIL (as path is currently returned as-is, i.e. `"./some_rel_path"`)

- [ ] **Step 3: Implement path resolution in `src/gangway/core/config.py`**
  
  At the end of `load_config` (right before returning `cfg`), add path resolution:
  ```python
      # 5. Resolve allowed_root if specified
      if cfg.allowed_root is not None:
          from pathlib import Path
          cfg.allowed_root = str(Path(cfg.allowed_root).resolve())
  ```

- [ ] **Step 4: Run test to verify it passes**
  
  Run: `uv run pytest tests/test_config.py`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  
  Run:
  ```bash
  git add src/gangway/core/config.py tests/test_config.py
  git commit -m "feat: resolve allowed_root to absolute path using Path.resolve()"
  ```

---

### Task 2: Refactor TOML loading to avoid redundant file opening

**Files:**
- Modify: `src/gangway/core/config.py`

**Interfaces:**
- Consumes: `load_config`
- Produces: File loading logic where JSON files are opened in 'r' mode and TOML files are opened in 'rb' mode, without overlapping open blocks.

- [ ] **Step 1: Refactor file opening structure**
  
  Replace the block under `# 3. Apply Config File (supports JSON/TOML)` in `src/gangway/core/config.py` with:
  ```python
      # 3. Apply Config File (supports JSON/TOML)
      if config_file and os.path.exists(config_file):
          data = {}
          if config_file.endswith(".json"):
              with open(config_file, "r") as f:
                  data = json.load(f)
          elif config_file.endswith(".toml"):
              # fallback minimal parser
              import sys

              if sys.version_info >= (3, 11):
                  import tomllib

                  with open(config_file, "rb") as bf:
                      data = tomllib.load(bf)
              else:
                  try:
                      import tomli as toml

                      with open(config_file, "rb") as bf:
                          data = toml.load(bf)
                  except ImportError:
                      pass
  ```

- [ ] **Step 2: Run all tests to verify no regressions**
  
  Run: `uv run pytest tests/test_config.py`
  Expected: PASS

- [ ] **Step 3: Commit changes**
  
  Run:
  ```bash
  git add src/gangway/core/config.py
  git commit -m "refactor: clean up TOML loading to avoid opening file twice"
  ```

---

### Task 3: Wrap port casting with try-except to handle invalid integer casting gracefully

**Files:**
- Modify: `src/gangway/core/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: `load_config`
- Produces: Port casting logic that raises descriptive `ValueError` upon invalid port formats.

- [ ] **Step 1: Write tests for invalid port formats**
  
  Add `test_load_config_invalid_ports` to `tests/test_config.py`.
  ```python
  import pytest

  def test_load_config_invalid_ports():
      # 1. Invalid port in environment variables
      os.environ["GANGWAY_PORT"] = "invalid_port"
      try:
          with pytest.raises(ValueError) as excinfo:
              load_config()
          assert "Invalid port in environment variable GANGWAY_PORT" in str(excinfo.value)
      finally:
          os.environ.pop("GANGWAY_PORT", None)

      # 2. Invalid port in config file
      with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
          json.dump({"port": "invalid_port"}, f)
          config_path = f.name
      try:
          with pytest.raises(ValueError) as excinfo:
              load_config(config_file=config_path)
          assert "Invalid port in configuration file" in str(excinfo.value)
      finally:
          os.unlink(config_path)

      # 3. Invalid port in CLI args
      with pytest.raises(ValueError) as excinfo:
          load_config(port="invalid_port")
      assert "Invalid port" in str(excinfo.value)
  ```

- [ ] **Step 2: Run tests to verify they fail**
  
  Run: `uv run pytest tests/test_config.py -k test_load_config_invalid_ports`
  Expected: FAIL

- [ ] **Step 3: Implement try-except for port casting in `src/gangway/core/config.py`**
  
  Wrap all integer casts for `port` in try-except blocks:
  In Env section:
  ```python
      if env_port:
          try:
              cfg.port = int(env_port)
          except ValueError as e:
              raise ValueError(f"Invalid port in environment variable GANGWAY_PORT: {env_port}") from e
  ```
  In config file parsing:
  ```python
              if "port" in data:
                  try:
                      cfg.port = int(data["port"])
                  except ValueError as e:
                      raise ValueError(f"Invalid port in configuration file: {data['port']}") from e
  ```
  In CLI overriding:
  ```python
      if port is not None:
          try:
              cfg.port = int(port)
          except ValueError as e:
              raise ValueError(f"Invalid port: {port}") from e
  ```

- [ ] **Step 4: Run all tests to verify they pass**
  
  Run: `uv run pytest tests/test_config.py`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  
  Run:
  ```bash
  git add src/gangway/core/config.py tests/test_config.py
  git commit -m "fix: wrap port integer casting with try-except to handle errors gracefully"
  ```
