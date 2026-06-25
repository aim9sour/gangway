# Design Specification: GitHub Repository & CI/CD Setup for 'gangway'

**Date**: 2026-06-25  
**Author**: Antigravity (AI Assistant)  
**Status**: Draft  
**Target Repository**: `abdullahmansour/gangway`  

---

## 1. Goal & Context
Now that the minimal `gangway` package has been successfully reserved on PyPI, we need to establish a professional GitHub repository. This involves creating a public repository, setting up automated continuous integration (CI) and continuous deployment (CD) workflows, creating community health files, and setting up issue/PR templates to align with open-source best practices.

---

## 2. Technical Stack & Tools
* **GitHub CLI (`gh`)**: For repository creation.
* **GitHub Actions**: For CI (linting, formatting, testing, build check) and CD (trusted publishing to PyPI).
* **Ruff**: For fast python linting and formatting.
* **Pytest**: For testing.
* **uv**: For managing the virtual environment and workflow steps.

---

## 3. Project Structure & New Files
The following files will be added to the repository:

```text
gangway/
├── .github/
│   ├── issue_template/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── CODE_OF_CONDUCT.md
└── CONTRIBUTING.md
```

---

## 4. Workflows Configuration

### 4.1 CI Workflow (`.github/workflows/ci.yml`)
Triggers on: `push` and `pull_request` to `main`.
Steps:
1. Checkout code.
2. Setup Python.
3. Install `uv`.
4. Run `ruff check` (linting).
5. Run `ruff format --check` (formatting).
6. Run `pytest` (testing).
7. Run `uv build` (packaging check).

### 4.2 Release Workflow (`.github/workflows/release.yml`)
Triggers on: GitHub Release publication.
Authentication: Uses OpenID Connect (OIDC) Trusted Publishing to fetch short-lived tokens from PyPI.
Permissions:
```yaml
permissions:
  id-token: write
```
Steps:
1. Checkout code.
2. Install `uv`.
3. Build package: `uv build`.
4. Publish package to PyPI: `uv publish`.

---

## 5. Community & Collaboration Templates

### 5.1 CODE_OF_CONDUCT.md
Standard Contributor Covenant Code of Conduct.

### 5.2 CONTRIBUTING.md
Detailed guidelines on how to clone, install dependencies via `uv sync` or `uv pip install`, run tests, format code, and submit pull requests.

### 5.3 Issue & Pull Request Templates
* **Bug Report**: Fields for description, steps to reproduce, expected behavior, screenshots, and environment details.
* **Feature Request**: Fields for context, proposed solution, and alternative considerations.
* **PR Template**: Checklist for tests passing, documentation updated, and description of changes.

---

## 6. Execution Steps
1. **Scaffold Files**: Write the workflows, templates, and community documents.
2. **Create GitHub Repo**: Run `gh repo create gangway --public --source=. --remote=origin`.
3. **Commit & Push**: Add all new files, commit, and push to `main` branch: `git push -u origin main`.
4. **Link PyPI to GitHub (Trusted Publishing)**:
   - User goes to `https://pypi.org/manage/project/gangway/settings/publishing/`.
   - Add publisher:
     - Publisher Name: **GitHub**
     - Owner: **abdullahmansour**
     - Repository: **gangway**
     - Workflow Name: **release.yml**
     - Environment Name: **pypi** (optional/recommended)
