# Changelog

All notable changes to AgencyOS are documented here.

## [3.0.0] - 2025-12-08

### 🚀 Major Release: GUI-Only Edition

#### Added
- **Desktop GUI** (PyQt6) with 8 main views
- **36+ AI tools** across 7 categories
- **Modern dark theme** with glassmorphism
- Real-time system monitoring dashboard
- Job queue with visual progress tracking

#### Removed
- ❌ Web UI (Streamlit)
- ❌ CLI (Typer)
- ❌ FastAPI endpoints
- Removed dependencies: streamlit, typer, rich, fastapi, uvicorn

#### Changed
- Entry point: `python -m social_media_manager.gui.main`
- Default LLM: Gemini 2.0 Flash
- Version bump to 3.0.0

---

## [2.1.0] - 2025-12-01

### Added
- VoxCPM TTS integration
- AI web search capability
- VisualRAG video indexing

---

## [2.0.0] - 2025-11-15

### Added
- Multi-provider LLM support (Gemini, Groq, Ollama)
- Background job queue
- Video production pipeline
