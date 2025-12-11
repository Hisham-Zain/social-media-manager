---
description: Safe refactoring workflow with test validation
---

# Refactor Workflow

Use this workflow when improving code quality without changing behavior.

## Steps

// turbo
1. **Ensure tests pass before refactoring**:
```bash
pytest -v
```

2. **Identify the refactoring scope**:
   - What code needs improvement?
   - What pattern should it follow?
   - Are there existing similar patterns to match?

3. **Make small, incremental changes**:
   - Rename variables/functions for clarity
   - Extract repeated code into functions
   - Split large functions (max 50 lines)
   - Split large files (max 500 lines)

// turbo
4. **Run tests after each change**:
```bash
pytest -v --tb=short
```

5. **Update imports and references** across the codebase if symbols were renamed.

// turbo
6. **Run linter and type checker**:
```bash
ruff check . --fix && mypy .
```

7. **Review the diff** to ensure behavior hasn't changed:
```bash
git diff
```

8. **Commit with refactor type**:
```bash
git commit -m "refactor(scope): description"
```
