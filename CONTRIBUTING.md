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
