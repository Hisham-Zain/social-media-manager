---
description: Git branching and merging workflow
---

# Git Flow Workflow

Use this workflow for branch management and merging.

## Starting a New Feature

1. **Ensure main is up to date**:
```bash
git checkout main && git pull origin main
```

2. **Create a feature branch**:
```bash
git checkout -b feature/short-description
```

3. **Make commits** with conventional messages:
```bash
git commit -m "feat(scope): description"
```

## Preparing to Merge

// turbo
1. **Fetch latest main**:
```bash
git fetch origin main
```

2. **Rebase onto main** (or merge if preferred):
```bash
git rebase origin/main
```

3. **Resolve any conflicts** if they occur.

// turbo
4. **Run all checks**:
```bash
ruff check . && mypy . && pytest -v
```

5. **Push the branch**:
```bash
git push origin feature/short-description
```

6. **Create a pull request** or merge directly if authorized.

## Commit Message Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change, no feature/fix |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |
