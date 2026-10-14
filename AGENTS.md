# Repository Guidelines

This document describes the structure, conventions, and workflows for contributors to this repository.

## Project Structure

```
AiCourse/
├── backend/         # FastAPI routes, models, migrations, CLI tools
├── frontend/        # Static HTML, CSS, and JavaScript
├── tests/           # Backend regression tests
├── data/            # SQLite database
├── uploads/         # Uploaded files and QR codes
├── notebooks/
└── README.md
```

## Build, Test, and Run

| Command | Purpose |
|---------|---------|
| `venv/bin/pip install -r backend/requirements.txt` | Install dependencies. |
| `PYTHONPATH=backend venv/bin/python -m unittest discover -s tests -v` | Run regression tests. |
| `PYTHONPATH=backend venv/bin/uvicorn main:app --app-dir backend` | Start the API and frontend. |

## Coding Style

- **Python**: Follow PEP 8. Use `ruff` for linting and formatting.
- **Indentation**: 4 spaces per level. No tabs.
- **Naming**: `snake_case` for functions, methods, and variables; `PascalCase` for classes; `UPPER_CASE` for constants.
- **Type hints**: Required on all public function signatures. Use `from __future__ import annotations` in Python 3.9+ modules.
- **Imports**: Group as standard library, third-party, then local. Each group separated by a blank line. Use absolute imports.

Run `uv run ruff check .` and `uv run ruff format .` before committing.

## Testing Guidelines

- **Framework**: Python `unittest` with `TestClient` for API checks.
- **Coverage**: All new code must include tests. Aim for 80%+ line coverage on changed files.
- **Test naming**: `test_<feature>_<scenario>` — e.g. `test_tokenize_empty_string`.
- **Test location**: Each `tests/` directory mirrors a `src/` module path. For `src/models/transformer.py`, write `tests/models/test_transformer.py`.
- **Running**: `PYTHONPATH=backend venv/bin/python -m unittest discover -s tests -v`.

## Commit & Pull Request Guidelines

### Commit Messages

Use the imperative mood. Keep the subject line under 72 characters.

```
feat: add attention masking to transformer layer
fix: handle empty dataset in data loader
docs: update installation steps in README
chore: bump torch to 2.1.0
```

### Pull Requests

- Title the PR using the same imperative style as commits.
- Describe what the change does and why, not how.
- Link related issues with `Closes #123` or `Related to #456`.
- Keep PRs focused on a single concern. Split large changes across multiple PRs.

## Agent-Specific Instructions

Files in `.agents/` contain per-agent system prompts that customize how LLM coding agents (Codex, Cursor, Copilot, etc.) behave in this repository. These prompts are scoped to the agent's tier or name — for example, `.agents/codex/SYSTEM.md` applies only when Codex is active. Each prompt should define role, constraints, and workflow preferences specific to the agent's interaction with this project.
