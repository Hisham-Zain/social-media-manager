---
description: Review code changes before merging
---

# Code Review Workflow

Use this workflow when reviewing code for quality and correctness.

## Steps

1. **Understand the change**: Read the PR description or commit messages.

// turbo
2. **View the diff**:
```bash
git diff main...HEAD
```

3. **Check for code quality issues**:
   - [ ] Functions under 50 lines?
   - [ ] Files under 500 lines?
   - [ ] Type hints on all functions?
   - [ ] Docstrings on public APIs?
   - [ ] No hardcoded secrets or credentials?
   - [ ] Error handling present?

// turbo
4. **Run linter and type checker**:
```bash
ruff check . && mypy .
```

// turbo
5. **Run tests**:
```bash
pytest -v
```

6. **Check for security issues**:
   - Input validation present?
   - No SQL injection risks?
   - Sensitive data not logged?

7. **Check for performance issues**:
   - No N+1 query patterns?
   - Expensive operations cached?
   - Async used for I/O bound tasks?

8. **Provide feedback** or approve the changes.
