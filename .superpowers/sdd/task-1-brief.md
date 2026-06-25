### Task 1: Project Scaffolding

**Files:**
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/pyproject.toml`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/README.md`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/LICENSE`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/__init__.py`
- Create: `C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/main.py`

**Interfaces:**
- Produces: Package source code and project configuration files ready for building.

- [ ] **Step 1: Initialize Git repo (if not already done) and setup directory**
  Run command in `C:/Users/abdo/.gemini/antigravity/scratch`:
  `git init gangway`
  Expected: Initialized empty Git repository in the `gangway` directory.

- [ ] **Step 2: Initialize uv project library**
  Run command in `C:/Users/abdo/.gemini/antigravity/scratch/gangway`:
  `uv init --lib .`
  Expected: Created a python package scaffolding.

- [ ] **Step 3: Write metadata configuration to pyproject.toml**
  Overwrite the generated `pyproject.toml` with:
  ```toml
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [project]
  name = "gangway"
  version = "0.1.0"
  description = "A smart Agent-to-Server Bridge connecting AI agents to remote environments as an MCP server and REST API."
  readme = "README.md"
  requires-python = ">=3.8"
  license = { text = "MIT" }
  authors = [
      { name = "Abdullah Mansour", email = "abdullahmansour.marketing@gmail.com" }
  ]
  classifiers = [
      "Development Status :: 3 - Alpha",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: MIT License",
      "Programming Language :: Python :: 3",
      "Programming Language :: Python :: 3.8",
      "Programming Language :: Python :: 3.9",
      "Programming Language :: Python :: 3.10",
      "Programming Language :: Python :: 3.11",
      "Programming Language :: Python :: 3.12",
  ]
  dependencies = []

  [project.urls]
  Homepage = "https://github.com/abdullahmansour/gangway"
  ```

- [ ] **Step 4: Create LICENSE file**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/LICENSE`:
  ```text
  MIT License

  Copyright (c) 2026 Abdullah Mansour

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
  ```

- [ ] **Step 5: Write README.md**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/README.md`:
  ```markdown
  # gangway

  A smart Agent-to-Server Bridge connecting AI agents (like Cursor and Claude Desktop) to remote environments (Kaggle, Colab, VPS) for full control, functioning as both an MCP server and REST API.

  ## Features

  * **Zero-Dependency Server**: Built using only Python standard library to prevent environment pollution or package conflicts on remote nodes.
  * **Context Optimization Tools**: Optimized tools for AIs (e.g., `preview_file`, `project_overview`, fast search) to save context window tokens.
  * **Background Job Control**: Execute and monitor long-running tasks asynchronously.
  * **Zero-Config Tunneling**: Integrated Cloudflare Tunnel to bypass NAT / firewalls.
  * **Directory State Management**: Keep track of the active working directory across execution contexts.

  ## Installation

  ```bash
  pip install gangway
  ```
  ```

- [ ] **Step 6: Setup minimal code files**
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/__init__.py`:
  ```python
  __version__ = "0.1.0"
  ```
  Write to `C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/main.py`:
  ```python
  def hello():
      return "Hello from gangway! The smart Agent-to-Server Bridge."

  if __name__ == "__main__":
      print(hello())
  ```

- [ ] **Step 7: Verify local packaging build**
  Run: `uv build` in `C:/Users/abdo/.gemini/antigravity/scratch/gangway`
  Expected: Build finishes successfully, generating wheel and sdist files in `dist/` directory.

- [ ] **Step 8: Commit files**
  Run:
  ```bash
  git add .
  git commit -m "chore: scaffold project and prepare name reservation metadata"
  ```
