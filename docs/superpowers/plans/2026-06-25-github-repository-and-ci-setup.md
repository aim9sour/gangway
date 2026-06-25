# GitHub Repository and CI/CD Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure a professional GitHub repository structure, templates, and actions, create a public GitHub repository using `gh` CLI, and push the local commits.

**Architecture:** Add standard community guidelines (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`) and workflows. Configure CI with `ruff` and `pytest` using `uv`, and CD via Trusted Publishing to PyPI. Push files to a new GitHub repository under the user's account.

**Tech Stack:** Python, `uv`, GitHub Actions, GitHub CLI (`gh`), Git

## Global Constraints

- Target Repository Name: `gangway`
- Target Owner: `abdullahmansour`
- Repository Visibility: Public
- Build Backend: `hatchling`
- Lint/Format Tool: `ruff`
- Trusted Publishing Environment: `pypi`

---

### Task 1: Add Community Documents & Templates

**Files:**
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/CONTRIBUTING.md`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/CODE_OF_CONDUCT.md`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/pull_request_template.md`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/issue_template/bug_report.md`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/issue_template/feature_request.md`

**Interfaces:**
- Produces: Standards and templates for open-source participation.

- [ ] **Step 1: Write CONTRIBUTING.md**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/CONTRIBUTING.md`:
  ```markdown
  # Contributing to gangway

  Thank you for your interest in contributing! This project is managed using `uv`.

  ## Getting Started

  1. Clone the repository:
     ```bash
     git clone https://github.com/abdullahmansour/gangway.git
     cd gangway
     ```
  2. Setup the development environment and virtual environment:
     ```bash
     uv sync
     ```
  3. Activate the virtual environment:
     * On Windows: `.venv\Scripts\activate`
     * On Linux/macOS: `source .venv/bin/activate`

  ## Coding Standards

  We use `ruff` for linting and formatting. Run:
  ```bash
  uv run ruff check .
  uv run ruff format .
  ```

  ## Running Tests

  Run the test suite using:
  ```bash
  uv run pytest
  ```

  ## Submitting Changes

  1. Create a branch: `git checkout -b feat/your-feature`.
  2. Write your changes and add tests.
  3. Ensure all tests pass and lint checks are clean.
  4. Submit a Pull Request.
  ```

- [ ] **Step 2: Write CODE_OF_CONDUCT.md**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/CODE_OF_CONDUCT.md`:
  ```markdown
  # Contributor Covenant Code of Conduct

  ## Our Pledge

  We as members, contributors, and leaders pledge to make participation in our
  community a harassment-free experience for everyone, regardless of age, body
  size, visible or invisible disability, ethnicity, sex characteristics, gender
  identity and expression, level of experience, education, socio-economic status,
  nationality, personal appearance, race, caste, color, religion, or sexual
  identity and orientation.

  We pledge to act and interact in ways that contribute to an open, welcoming,
  diverse, inclusive, and healthy community.

  ## Our Standards

  Examples of behavior that contributes to a positive environment for our
  community include:

  * Demonstrating empathy and kindness toward other people
  * Being respectful of differing opinions, viewpoints, and experiences
  * Giving and gracefully receiving constructive feedback
  * Accepting responsibility and apologizing to those affected by our mistakes,
    and learning from the experience
  * Focusing on what is best for the overall community

  Examples of unacceptable behavior include:

  * The use of sexualized language or imagery, and unwelcome sexual attention or
    advances
  * Trolling, insulting or derogatory comments, and personal or political attacks
  * Public or private harassment
  * Publishing others' private information, such as a physical or email
    address, without their explicit permission
  * Other conduct which could reasonably be considered inappropriate in a
    professional setting

  ## Enforcement Responsibilities

  Community leaders are responsible for clarifying and enforcing our standards of
  acceptable behavior and will take appropriate and fair corrective action in
  response to any behavior they deem inappropriate, threatening, offensive,
  or harmful.

  For questions or to report an issue, please contact the maintainer at
  `abdullahmansour.marketing@gmail.com`.
  ```

- [ ] **Step 3: Create Issue Template Directory**
  Ensure the directory `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/issue_template` exists.

- [ ] **Step 4: Write bug_report.md issue template**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/issue_template/bug_report.md`:
  ```markdown
  ---
  name: Bug report
  about: Create a report to help us improve
  title: '[BUG] '
  labels: bug
  assignees: ''
  ---

  **Describe the bug**
  A clear and concise description of what the bug is.

  **To Reproduce**
  Steps to reproduce the behavior.

  **Expected behavior**
  A clear and concise description of what you expected to happen.

  **Environment Details**
  - OS: [e.g. Windows, Ubuntu, macOS]
  - Python Version: [e.g. 3.10]
  - Gangway Version: [e.g. 0.1.0]

  **Additional Context**
  Add any other context about the problem here (logs, traces).
  ```

- [ ] **Step 5: Write feature_request.md issue template**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/issue_template/feature_request.md`:
  ```markdown
  ---
  name: Feature request
  about: Suggest an idea for this project
  title: '[FEAT] '
  labels: enhancement
  assignees: ''
  ---

  **Is your feature request related to a problem? Please describe.**
  A clear and concise description of what the problem is.

  **Describe the solution you'd like**
  A clear and concise description of what you want to happen.

  **Describe alternatives you've considered**
  A clear and concise description of any alternative solutions or features you've considered.

  **Additional context**
  Add any other context or screenshots about the feature request here.
  ```

- [ ] **Step 6: Write pull_request_template.md**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/pull_request_template.md`:
  ```markdown
  ## Description

  Please include a summary of the changes and the related issue.

  ## Type of Change

  - [ ] Bug fix (non-breaking change which fixes an issue)
  - [ ] New feature (non-breaking change which adds functionality)
  - [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
  - [ ] Documentation update

  ## Checklist

  - [ ] My code follows the style guidelines of this project
  - [ ] I have run `ruff check` and `ruff format` on my changes
  - [ ] I have added tests that prove my fix is effective or that my feature works
  - [ ] New and existing unit tests pass locally with my changes
  ```

- [ ] **Step 7: Verify files exist locally**
  Check directories and verify files are present.

- [ ] **Step 8: Commit files**
  Run:
  ```bash
  git add .github/ CONTRIBUTING.md CODE_OF_CONDUCT.md
  git commit -m "docs: add issue templates, PR template, and contributing guidelines"
  ```

---

### Task 2: Configure CI/CD GitHub Actions

**Files:**
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/workflows/ci.yml`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/workflows/release.yml`

**Interfaces:**
- Consumes: Project source code and configuration files.

- [ ] **Step 1: Write ci.yml workflow**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/workflows/ci.yml`:
  ```yaml
  name: CI

  on:
    push:
      branches: [ main ]
    pull_request:
      branches: [ main ]

  jobs:
    test:
      runs-on: ubuntu-latest
      strategy:
        matrix:
          python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]

      steps:
        - uses: actions/checkout@v4

        - name: Set up Python ${{ matrix.python-version }}
          uses: actions/setup-python@v5
          with:
            python-version: ${{ matrix.python-version }}

        - name: Install uv
          uses: astral-sh/setup-uv@v5
          with:
            enable-cache: true

        - name: Install dependencies
          run: uv sync

        - name: Lint and Format Checks
          run: |
            uv run ruff check .
            uv run ruff format --check .

        - name: Run Tests
          run: uv run pytest

        - name: Build check
          run: uv build
  ```

- [ ] **Step 2: Write release.yml workflow**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/.github/workflows/release.yml`:
  ```yaml
  name: Release

  on:
    release:
      types: [published]

  jobs:
    pypi-publish:
      name: Publish release to PyPI
      runs-on: ubuntu-latest
      environment: pypi
      permissions:
        id-token: write  # Mandatory for Trusted Publishing OIDC
      steps:
        - uses: actions/checkout@v4

        - name: Install uv
          uses: astral-sh/setup-uv@v5

        - name: Build package
          run: uv build

        - name: Publish package to PyPI
          run: uv publish
  ```

- [ ] **Step 3: Setup minimal test stub to make CI pass**
  Create directory `C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests`.
  Create file `C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_main.py`:
  ```python
  from gangway.main import hello

  def test_hello():
      assert hello() == "Hello from gangway! The smart Agent-to-Server Bridge."
  ```

- [ ] **Step 4: Add pytest dependency to pyproject.toml**
  Open `C:/Users/abdo/.gemini/antigravity/scratch/gangway/pyproject.toml` and modify to add `pytest` in dependency group:
  ```toml
  [dependency-groups]
  dev = [
      "pytest>=8.0.0",
      "ruff>=0.3.0",
  ]
  ```

- [ ] **Step 5: Verify tests run locally**
  Run: `uv run pytest` in `C:/Users/abdo/.gemini/antigravity/scratch/gangway`
  Expected: pytest runs and passes the main test.

- [ ] **Step 6: Commit workflows and test**
  Run:
  ```bash
  git add .github/workflows/ tests/ pyproject.toml
  git commit -m "ci: configure GitHub Actions test/release workflows and add pytest tests"
  ```

---

### Task 3: GitHub Repository Creation and Code Upload

**Files:** None modified.

**Interfaces:**
- Consumes: The committed Git repository history.

- [ ] **Step 1: Check gh CLI authentication status**
  Run command in `C:/Users/abdo/.gemini/antigravity/scratch/gangway`:
  `gh auth status`
  Expected: Shows logged in to github.com as abdullahmansour or similar.

- [ ] **Step 2: Create repository on GitHub**
  Run command:
  `gh repo create gangway --public --source=. --remote=origin --push`
  Expected: Public repository `gangway` is created on GitHub, the local `origin` remote is added, and the local commits are pushed to `main` branch.

- [ ] **Step 3: Verify repository exists**
  Run: `gh repo view --web` to open browser or check CLI repository status.
  Expected: Repository is successfully online.
