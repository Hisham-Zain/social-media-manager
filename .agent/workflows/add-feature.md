---
description: Step-by-step workflow for adding a new feature to the project
---

# Add New Feature Workflow

Use this workflow when implementing a new feature.

## Steps

1. **Understand the requirement**: Clearly define what the feature should do before writing code.

2. **Create an implementation plan**: Draft a plan with:
   - Files to create or modify
   - Dependencies needed
   - Test cases to write

3. **Check for existing patterns**: Search the codebase for similar implementations:
```bash
grep -r "similar_pattern" src/
```

4. **Implement the feature**:
   - Create new files in the appropriate directory
   - Follow existing code patterns
   - Add type hints and docstrings

5. **Write tests**: Create unit tests in `tests/unit/` covering:
   - Happy path scenarios
   - Edge cases
   - Error handling

// turbo
6. **Run quality checks**:
```bash
ruff check . && mypy . && pytest -v
```

7. **Update documentation** if needed (README, docstrings, etc.)

8. **Commit with conventional commit message**:
```bash
git add . && git commit -m "feat(scope): description"
```
