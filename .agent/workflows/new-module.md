---
description: Create a new Python module with proper boilerplate
---

# New Module Workflow

Use this workflow when creating a new Python module.

## Steps

1. **Decide the module location**: Choose the appropriate directory under `src/`.

2. **Create the module file** with standard structure:
```python
"""
Module description.

This module provides...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # Type-only imports here

logger = logging.getLogger(__name__)


class ModuleName:
    """Class docstring."""

    def __init__(self) -> None:
        """Initialize the module."""
        pass
```

3. **Update `__init__.py`**: Export the new class/functions from the package's `__init__.py`.

4. **Create test file** at `tests/unit/test_module_name.py`:
```python
"""Tests for module_name."""

import pytest
from package.module_name import ModuleName


class TestModuleName:
    """Test cases for ModuleName."""

    def test_initialization(self) -> None:
        """Test basic initialization."""
        instance = ModuleName()
        assert instance is not None
```

// turbo
5. **Verify the module imports correctly**:
```bash
python -c "from package.module_name import ModuleName; print('OK')"
```

// turbo
6. **Run tests**:
```bash
pytest tests/unit/test_module_name.py -v
```
