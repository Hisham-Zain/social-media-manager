# 🤝 Contributing to AgencyOS

Thank you for your interest in contributing!

---

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/social-media-manager.git
cd social-media-manager
```

### 2. Setup Development Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3. Run Tests

```bash
pytest tests/
```

---

## Development Workflow

### Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/<description>` | `feature/add-tiktok-upload` |
| Bugfix | `fix/<issue-id>-<description>` | `fix/123-memory-leak` |
| Hotfix | `hotfix/<description>` | `hotfix/crash-on-startup` |

### Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```
feat(ai): add Anthropic Claude provider
fix(gui): resolve memory leak in timeline
docs: update configuration guide
```

---

## Code Standards

### Python Style
- **PEP 8** compliance
- **Type hints** on all functions
- **Docstrings** in Google format

### Linting

```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Type checking
mypy src/
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src

# Specific test file
pytest tests/test_brain.py
```

---

## Project Structure

```
src/social_media_manager/
├── ai/          # AI engines
├── core/        # Business logic
├── gui/         # Desktop interface
├── platforms/   # Social integrations
└── plugins/     # Plugin system

tests/
├── unit/        # Unit tests
└── integration/ # Integration tests
```

---

## Submitting Changes

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

- Write code with type hints
- Add/update tests
- Update documentation

### 3. Run Checks

```bash
ruff check .
mypy src/
pytest
```

### 4. Commit & Push

```bash
git add .
git commit -m "feat(scope): description"
git push origin feature/my-feature
```

### 5. Open Pull Request

- Use descriptive title
- Reference related issues
- Describe changes made

---

## Adding New AI Engines

1. Create module in `src/social_media_manager/ai/`
2. Implement engine class
3. Add to `ai/__init__.py` exports
4. Create UI in `gui/views/ai_tools.py` or as plugin
5. Add tests in `tests/unit/`
6. Document in `docs/features/ai-tools.md`

---

## Need Help?

- Check existing [Issues](https://github.com/youruser/social-media-manager/issues)
- Open a [Discussion](https://github.com/youruser/social-media-manager/discussions)
