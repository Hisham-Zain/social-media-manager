---
description: Systematic debugging workflow for tracking down bugs
---

# Debug Workflow

Use this workflow when investigating and fixing bugs.

## Steps

1. **Reproduce the issue**: Get the exact error message or unexpected behavior.

2. **Locate the error source**: Search for the error or relevant code:
```bash
grep -rn "ErrorMessage" src/
```

3. **Understand the code flow**: Trace the execution path by reading:
   - The failing function
   - Functions that call it
   - Functions it calls

4. **Add diagnostic logging** (temporarily):
```python
import logging
logging.debug(f"Variable state: {variable}")
```

5. **Form a hypothesis**: Based on the evidence, hypothesize what's causing the bug.

6. **Test the hypothesis**: Make a minimal fix and test.

// turbo
7. **Verify the fix**:
```bash
pytest -v -k "test_related_to_bug"
```

8. **Clean up**: Remove debug logging, ensure no regressions.

// turbo
9. **Run full test suite**:
```bash
pytest -v
```

10. **Commit the fix**:
```bash
git commit -m "fix(scope): description of fix"
```
