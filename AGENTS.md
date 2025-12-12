# AGENTS.md

> Context and instructions for AI coding agents working on this project.

## Project Overview

**AgencyOS** is an AI-powered desktop application for social media content automation. Built with Python 3.10+, PyQt6 GUI, and integrated with 100+ LLM providers via LiteLLM.

## Quick Start

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Run GUI
./launch_gui.sh
# OR: python -m social_media_manager.gui.main

# Run tests
pytest
```

## Project Structure

```
src/social_media_manager/
├── ai/           # AI engines (brain.py is the LLM interface)
├── gui/          # PyQt6 desktop app (views/, widgets/)
├── core/         # Business logic, audio/video processing
├── platforms/    # Social media platform integrations
├── api.py        # FastAPI backend server
├── client.py     # API client for GUI ↔ backend
├── config.py     # Central configuration (reads .env)
└── database.py   # SQLAlchemy ORM models
```

## Key Patterns

### LLM Usage
All LLM calls go through `HybridBrain` in `ai/brain.py`:
```python
from social_media_manager.ai import HybridBrain
brain = HybridBrain()
response = brain.think("prompt", context="optional context")
```

### Async in GUI
Use `qasync` for async operations within PyQt:
```python
import asyncio
from qasync import asyncSlot

@asyncSlot()
async def on_button_click(self):
    result = await some_async_operation()
```

### Database Access
Use SQLAlchemy ORM via `DatabaseManager`:
```python
from social_media_manager.database import DatabaseManager
db = DatabaseManager()
with db.session() as session:
    # Use ORM models, never raw SQL
```

## Coding Standards

| Rule | Requirement |
|------|-------------|
| Type hints | Required on all public functions |
| Docstrings | Google style, required on public functions |
| Max function length | 50 lines |
| Max file length | 500 lines |
| Logging | Use `loguru` (never `print()`) |
| Testing | pytest, all new features need tests |

## Before Submitting Changes

```bash
ruff check .        # Linting
mypy .              # Type checking
pytest              # Tests
```

## Environment Variables

Key variables in `.env` (see `.env.example`):
- `LLM_PROVIDER` / `LLM_MODEL` - Primary LLM
- `GEMINI_API_KEY`, `GROQ_API_KEY` - Provider keys
- `PEXELS_API_KEY`, `PIXABAY_API_KEY` - Stock media

## Important Files

| File | Purpose |
|------|---------|
| `ai/brain.py` | Central LLM interface with fallback chain |
| `gui/main.py` | GUI entry point |
| `config.py` | All configuration management |
| `database.py` | SQLAlchemy models and DB manager |
| `job_queue.py` | Background job processing |

## Common Tasks

### Adding a New AI Feature
1. Create module in `src/social_media_manager/ai/`
2. Use `HybridBrain` for LLM calls
3. Export from `ai/__init__.py`
4. Add tests in `tests/unit/`

### Adding a GUI View
1. Create view in `gui/views/`
2. Register in `gui/main.py` navigation
3. Use existing widgets from `gui/widgets/`

### Adding an API Endpoint
1. Add route in `api.py`
2. Add client method in `client.py`
3. Follow existing patterns for error handling

## Don't

- ❌ Use raw SQL (use ORM)
- ❌ Hardcode API keys (use config)
- ❌ Use `print()` (use `logger`)
- ❌ Skip type hints
- ❌ Commit to main directly
