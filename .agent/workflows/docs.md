---
description: Generate or update project documentation
---

# Documentation Workflow

Use this workflow when creating or updating project documentation.

## Steps

1. **Audit existing documentation**:
   - Check README.md for accuracy
   - Review docstrings in key modules
   - Look for outdated information

2. **Update module docstrings**: Each public function should have:
```python
def function_name(param: Type) -> ReturnType:
    """Short description.

    Longer description if needed.

    Args:
        param: Description of parameter.

    Returns:
        Description of return value.

    Raises:
        ExceptionType: When this happens.
    """
```

3. **Update README.md** with:
   - Project description
   - Installation instructions
   - Usage examples
   - Configuration options
   - API reference (if applicable)

// turbo
4. **Generate API docs** (if using sphinx or mkdocs):
```bash
cd docs && make html
```

5. **Review generated docs** for completeness and accuracy.

6. **Commit documentation**:
```bash
git commit -m "docs: update documentation"
```
