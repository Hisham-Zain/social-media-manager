---
description: Run linting, type checking, and tests before committing
---

# Pre-Commit Quality Check

Run this workflow before committing code to ensure quality standards.

## Steps

// turbo
1. Run linter to check code style:
```bash
ruff check . --fix
```

// turbo
2. Run type checker:
```bash
mypy .
```

// turbo
3. Run unit tests with coverage:
```bash
pytest -v --tb=short
```

4. If any step fails, fix the issues and re-run the workflow.

5. Once all checks pass, the code is ready to commit.
