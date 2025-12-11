---
description: Set up a new Python project from scratch
---

# Project Setup Workflow

Use this workflow when starting a new Python project.

## Steps

// turbo
1. **Create project structure**:
```bash
mkdir -p src/project_name tests/unit tests/integration
touch src/project_name/__init__.py tests/__init__.py tests/conftest.py
```

2. **Create pyproject.toml**:
```toml
[project]
name = "project-name"
version = "0.1.0"
description = "Project description"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
```

3. **Create README.md** with:
   - Project name and description
   - Installation instructions
   - Usage examples

4. **Set up virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e ".[dev]"
```

5. **Initialize git**:
```bash
git init
echo ".venv/\n__pycache__/\n*.egg-info/\n.mypy_cache/" > .gitignore
git add . && git commit -m "chore: initial project setup"
```

// turbo
6. **Verify setup**:
```bash
python -c "import project_name; print('Setup complete!')"
```
