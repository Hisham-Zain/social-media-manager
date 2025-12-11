# AgencyOS - AI Social Media Manager

## Project Overview

**AgencyOS** is a comprehensive, AI-powered desktop application for automating social media content creation and management. It leverages a suite of AI engines to handle tasks ranging from script generation and video production to scheduling and analytics.

**Key Features:**
*   **Desktop GUI:** A modern interface built with PyQt6.
*   **AI "Brain":** Integrates multiple LLMs (Gemini, Groq, OpenAI) via `litellm`.
*   **Content Production:** Automated video editing, voice synthesis (VoxCPM), background removal, and upscaling.
*   **Automation:** Watch folders for auto-processing and job queues for background tasks.
*   **Asset Management:** Centralized media library and asset vault.

## Architecture

The project follows a modular Python structure located in `src/social_media_manager/`:

*   **`ai/`**: Contains specific AI agents/engines (e.g., `composer`, `director`, `voice_cloner`).
*   **`gui/`**: The PyQt6 desktop application code (`views`, `widgets`, `main.py`).
*   **`core/`**: Core business logic, including audio/video processing and orchestration.
*   **`platforms/`**: Integrations with social media platforms (e.g., YouTube, Instagram).
*   **`brain_data/`**: Storage for the ChromaDB vector database.

## Development Environment

### Prerequisites
*   Python 3.10+
*   FFmpeg (required for `moviepy` and video processing)
*   A valid `.env` file with API keys (see `.env.example`).

### Key Commands

**Setup & Installation:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**Running the Application:**
```bash
# Launch the Desktop GUI
./launch_gui.sh
# OR
python -m social_media_manager.gui.main
```

**Testing:**
```bash
# Run all tests
pytest
```

## Configuration

Configuration is managed via environment variables. Copy `.env.example` to `.env` and configure:
*   `LLM_PROVIDER` & `LLM_MODEL`: Primary AI model settings.
*   `GEMINI_API_KEY`, `GROQ_API_KEY`, etc.: Provider-specific keys.

## Coding Conventions

*   **Style:** Follows standard Python PEP 8 guidelines.
*   **Typing:** Type hints are used throughout the codebase.
*   **Async:** The GUI uses `qasync` to handle asynchronous operations within the PyQt event loop.
*   **Logging:** Uses `loguru` for logging.

## Important Files
*   `launch_gui.sh`: Shell script to easily launch the application.
*   `src/social_media_manager/gui/main.py`: Entry point for the GUI application.
*   `src/social_media_manager/config.py`: Central configuration management.
