# AgencyOS - Code Context

A comprehensive reference document for the Social Media Manager (AgencyOS) codebase.

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "Presentation Layer"
        GUI[Desktop GUI<br/>PyQt6]
        API[REST API<br/>FastAPI]
    end

    subgraph "Application Layer"
        Container[DI Container]
        Orchestrator[SocialMediaManager<br/>Orchestrator]
        JobQueue[Background<br/>Job Queue]
    end

    subgraph "Domain Layer"
        Brain[HybridBrain<br/>LLM Engine]
        AIEngines[39 AI Engines]
        Core[Core Processors]
        Plugins[Plugin System]
    end

    subgraph "Infrastructure Layer"
        DB[(Database<br/>PostgreSQL/SQLite)]
        Platforms[Social Platforms<br/>YouTube, Instagram]
        Storage[File Storage]
    end

    GUI --> Container
    API --> Container
    Container --> Orchestrator
    Container --> Brain
    Container --> JobQueue
    Orchestrator --> AIEngines
    Orchestrator --> Core
    AIEngines --> Brain
    JobQueue --> DB
    Orchestrator --> DB
    Core --> Storage
    Orchestrator --> Platforms
```

---

## 📁 Project Structure

```
social-media-manager/
├── src/social_media_manager/     # Main package
│   ├── ai/                       # 39 AI engines (brain, producer, etc.)
│   ├── api/                      # FastAPI server components
│   ├── automation/               # Watchdog, batch processing
│   ├── core/                     # Video/audio processors, orchestrator
│   ├── gui/                      # Desktop GUI (PyQt6)
│   │   ├── views/                # 8 main views
│   │   ├── widgets/              # Reusable UI components
│   │   └── styles.py             # Theme system
│   ├── platforms/                # YouTube, Instagram API integrations
│   ├── plugins/                  # Plugin architecture
│   ├── repositories/             # Data access layer (Repository Pattern)
│   ├── scripts/                  # Utility scripts
│   ├── api.py                    # FastAPI application factory
│   ├── client.py                 # API client for GUI→Server communication
│   ├── config.py                 # Configuration management
│   ├── container.py              # Dependency injection container
│   ├── database.py               # SQLAlchemy ORM models & manager
│   ├── dependencies.py           # FastAPI dependencies
│   ├── exceptions.py             # Custom exceptions
│   ├── job_queue.py              # Background job processing
│   ├── logging.py                # Loguru configuration
│   └── models.py                 # Pydantic models
├── tests/                        # Unit & integration tests
├── docs/                         # Documentation
├── .agent/                       # AI agent workflows
├── .env                          # Environment variables (API keys)
├── requirements.txt              # Python dependencies
└── setup.py                      # Package configuration
```

---

## 🔧 Key Components

### 1. Configuration (`config.py`)

Centralized configuration using environment variables:

```python
from social_media_manager.config import config

# LLM Settings (Fallback Chain: Gemini → Groq → Ollama)
config.LLM_PROVIDER           # Primary: "gemini"
config.LLM_MODEL              # "gemini-2.0-flash-exp"
config.LLM_FALLBACK_PROVIDER  # Fallback 1: "groq"
config.LLM_FALLBACK_MODEL     # "llama-3.2-3b-preview"
config.LLM_FALLBACK2_PROVIDER # Fallback 2: "ollama"
config.LLM_FALLBACK2_MODEL    # "llama3.2:3b"

# Image/Video Generation
config.IMAGE_PROVIDER         # "huggingface"
config.VIDEO_PROVIDER         # "huggingface"

# API Keys
config.GEMINI_API_KEY
config.GROQ_API_KEY
config.HF_TOKEN               # Hugging Face token
config.PEXELS_API_KEY
config.PIXABAY_API_KEY

# Database
config.DATABASE_URL           # PostgreSQL connection string

# Paths
config.BASE_DIR               # ~/.social_media_manager
config.PROCESSED_DIR          # Processed video output
config.GENERATED_DIR          # AI-generated content
config.WATCH_FOLDER           # Auto-process inbox
```

---

### 2. Dependency Injection Container (`container.py`)

Lazy-loaded service management:

```python
from social_media_manager.container import get_container

container = get_container()

# Access services (lazy-loaded)
brain = container.brain          # HybridBrain instance
db = container.db                # DatabaseManager instance
producer = container.producer    # VideoProducer instance
job_queue = container.job_queue  # JobQueue instance
orchestrator = container.orchestrator  # SocialMediaManager instance
```

**Available Services:**
| Property | Type | Description |
|----------|------|-------------|
| `brain` | `HybridBrain` | LLM operations with fallback chain |
| `db` | `DatabaseManager` | Database operations (SQLAlchemy) |
| `producer` | `VideoProducer` | Video generation pipeline |
| `job_queue` | `JobQueue` | Background task processing |
| `orchestrator` | `SocialMediaManager` | High-level workflow orchestration |

---

### 3. HybridBrain (`ai/brain.py`)

Unified LLM interface using LiteLLM with automatic fallback:

```python
from social_media_manager.ai.brain import HybridBrain

brain = HybridBrain()

# Basic inference
response = brain.think("Generate a viral hook for fitness content")

# JSON mode for structured output
data = brain.think("Generate 3 hashtags as JSON", json_mode=True)

# Web-enhanced thinking
result = brain.search_and_think(
    query="latest TikTok trends 2024",
    prompt="Summarize the top 3 trends"
)

# Research mode
research = brain.research_topic("AI video editing tools")
```

**Key Methods:**
| Method | Description |
|--------|-------------|
| `think(prompt, context, json_mode)` | Core LLM inference |
| `search_and_think(query, prompt)` | Web search + LLM analysis |
| `research_topic(topic)` | Comprehensive research |
| `generate_viral_hooks(topic)` | Generate content hooks |
| `extract_visual_keywords(transcript)` | Extract keywords for B-roll |
| `get_available_providers()` | List LLM providers with status |

**Fallback Chain:**
1. Primary: Gemini (`gemini-2.0-flash-exp`)
2. Fallback 1: Groq (`llama-3.2-3b-preview`)
3. Fallback 2: Ollama (`llama3.2:3b`)

---

### 4. Database (`database.py`)

SQLAlchemy ORM with PostgreSQL/SQLite support:

```python
from social_media_manager.database import DatabaseManager

db = DatabaseManager()

# Session management (context manager)
with db.get_session() as session:
    # ORM operations here
    pass

# Video tracking
video_id = db.add_video("intro.mp4", "/path/to/video", 60.0, "cinematic")

# Project management
project_id = db.create_project("My Video", platform="youtube")
project = db.get_project(project_id)
db.save_project_draft(project_id, script="...", audio_paths=[...])

# Analytics
analytics = db.get_analytics()
posts = db.get_all_posts()
```

**ORM Models:**
| Model | Table | Description |
|-------|-------|-------------|
| `Video` | `videos` | Tracked video files |
| `PostedContent` | `posted_content` | Published content |
| `Comment` | `comments` | Social media comments |
| `Project` | `projects` | Draft projects |
| `Asset` | `assets` | Media assets (vault) |

---

### 5. Job Queue (`job_queue.py`)

SQLite-backed background job processing:

```python
from social_media_manager.job_queue import JobQueue, JobPriority

queue = JobQueue(num_workers=2)
queue.start()

# Submit jobs
job_id = queue.submit(
    "video_render",
    {"script": "...", "avatar": "lisa"},
    priority=JobPriority.HIGH
)

# Monitor jobs
job = queue.get_job(job_id)
print(f"Status: {job.status}, Progress: {job.progress}%")

# Job management
queue.cancel_job(job_id)
queue.retry_job(job_id)
queue.clear_completed(older_than_hours=24)

queue.stop()
```

**Built-in Job Types:**
| Job Type | Handler | Description |
|----------|---------|-------------|
| `video_render` | `_handle_video_render` | Full video production |
| `ai_generate` | `_handle_ai_generate` | AI content generation |
| `batch_process` | `_handle_batch` | Batch file processing |
| `trend_scan` | `_handle_trend_scan` | Trend analysis |
| `forecast_trends` | `_handle_forecast_trends` | Engagement forecasting |

**Job States:**
- `PENDING` → `QUEUED` → `RUNNING` → `COMPLETED` / `FAILED` / `CANCELLED`

---

### 6. REST API (`api.py`)

FastAPI application with comprehensive endpoints:

```python
# Start server
# uvicorn social_media_manager.api:app --reload

from social_media_manager.api import create_app
app = create_app()
```

**Key Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/brain/think` | POST | Remote LLM inference |
| `/brain/status` | GET | Brain configuration |
| `/jobs` | GET | List all jobs |
| `/jobs` | POST | Submit new job |
| `/jobs/{id}` | GET | Get job status |
| `/jobs/{id}/cancel` | POST | Cancel job |
| `/storyboard` | POST | Generate storyboard |
| `/assets/search` | POST | Semantic asset search |
| `/content/generate` | POST | Generate content |
| `/schedule` | POST | Schedule content |

---

### 7. GUI Structure (`gui/`)

PyQt6 desktop application:

```python
# Launch GUI
python -m social_media_manager.gui.main
```

**Views (8 total):**
| View | File | Description |
|------|------|-------------|
| Dashboard | `dashboard.py` | Stats, activity feed, quick actions |
| Content Studio | `content_studio.py` | Script → Production workflow |
| Media Library | `media_library.py` | Visual search, video indexing |
| Automation | `automation.py` | Batch jobs, watch folders |
| Strategy Room | `strategy.py` | Prompts, forecasting, trends |
| AI Tools | `ai_tools.py` | 36+ AI tools in 7 categories |
| Job Queue | `job_queue.py` | Background task monitor |
| Settings | `settings.py` | API keys, LLM config |

**Widgets:**
| Widget | File | Description |
|--------|------|-------------|
| Kanban | `kanban.py` | Content status board |
| Timeline | `timeline.py` | Video timeline editor |
| Media Player | `media_player.py` | Video preview |
| Toasts | `toasts.py` | Notification system |

---

## 🤖 AI Engines (39 total)

Located in `src/social_media_manager/ai/`:

### Content Generation
| Engine | File | Description |
|--------|------|-------------|
| `HybridBrain` | `brain.py` | Central LLM interface |
| `VideoProducer` | `producer.py` | Full video pipeline |
| `AIDirector` | `director.py` | Scene direction |
| `MusicComposer` | `composer.py` | AI music generation |
| `VoxCPMEngine` | `voxcpm_engine.py` | Text-to-speech |

### Analysis & Research
| Engine | File | Description |
|--------|------|-------------|
| `ContentAnalyzer` | `analyzer.py` | Content analysis |
| `TrendRadar` | `radar.py` | Trend detection |
| `EngagementForecaster` | `forecaster.py` | Engagement prediction |
| `SEOAgent` | `seo_agent.py` | SEO optimization |
| `WebSearcher` | `searcher.py` | DuckDuckGo search |

### Media Processing
| Engine | File | Description |
|--------|------|-------------|
| `BackgroundRemover` | `background_remover.py` | BG removal |
| `VideoUpscaler` | `upscaler.py` | AI upscaling |
| `VoiceCloner` | `voice_cloner.py` | Voice cloning |
| `AIAvatar` | `avatar.py` | Talking head generation |
| `Transcriber` | `transcriber.py` | Speech-to-text |

### Intelligence
| Engine | File | Description |
|--------|------|-------------|
| `VisualRAG` | `visual_rag.py` | Semantic visual search |
| `RAGEngine` | `rag.py` | Document retrieval |
| `ViralCloner` | `viral_cloner.py` | Viral video analysis |
| `StyleTuner` | `style_tuner.py` | Style transfer |
| `ABOptimizer` | `ab_optimizer.py` | A/B testing |

---

## 🔌 Core Processors (`core/`)

| Processor | File | Description |
|-----------|------|-------------|
| `VideoProcessor` | `processor.py` | FFmpeg-based video processing |
| `SocialMediaManager` | `orchestrator.py` | High-level workflow orchestration |
| `AssetVault` | `asset_vault.py` | Smart asset management |
| `DynamicCaptions` | `dynamic_captions.py` | Auto-captioning |
| `ProjectState` | `project_state.py` | Project persistence |
| `ContentScheduler` | `scheduler.py` | Content scheduling |
| `SystemMonitor` | `system_monitor.py` | Resource monitoring |
| `NotificationManager` | `notifications.py` | User notifications |
| `UsageTracker` | `usage_tracker.py` | API usage tracking |

---

## 🗄️ Data Access (Repository Pattern)

Located in `src/social_media_manager/repositories/`:

```python
from social_media_manager.repositories.unit_of_work import get_unit_of_work
from social_media_manager.repositories.job_repository import JobRepository

# Using Unit of Work pattern
with get_unit_of_work() as uow:
    job_repo = JobRepository(uow.session)
    jobs = job_repo.get_pending_jobs()
    uow.commit()
```

---

## 🌐 Platform Integrations (`platforms/`)

| Platform | File | Features |
|----------|------|----------|
| YouTube | `youtube.py` | Upload, analytics, comments |
| Instagram | `instagram.py` | Reels, stories, posts |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=social_media_manager

# Run specific test
pytest tests/test_ai_brain.py
```

**Test Files:**
| File | Coverage |
|------|----------|
| `test_ai_brain.py` | HybridBrain tests |
| `test_core_processor.py` | VideoProcessor tests |
| `test_connections.py` | OAuth connection tests |
| `test_tts.py` | Text-to-speech tests |
| `integration_test.py` | End-to-end tests |

---

## 🚀 Running the Application

### Desktop GUI
```bash
# Method 1: Module
python -m social_media_manager.gui.main

# Method 2: Script
./launch_gui.sh
```

### API Server
```bash
uvicorn social_media_manager.api:app --reload --port 8000
```

### Background Workers
```python
from social_media_manager.job_queue import JobQueue

queue = JobQueue(num_workers=4, auto_start=True)
# Workers start processing automatically
```

---

## 📊 Data Flow

```mermaid
sequenceDiagram
    participant User
    participant GUI
    participant Container
    participant Brain
    participant JobQueue
    participant Database

    User->>GUI: Create Video Request
    GUI->>Container: Get services
    Container->>Brain: Generate script
    Brain-->>GUI: Script response
    GUI->>JobQueue: Submit render job
    JobQueue->>Database: Save job
    JobQueue-->>GUI: Job ID

    loop Background Processing
        JobQueue->>JobQueue: Process job
        JobQueue->>Database: Update progress
    end

    JobQueue->>Database: Mark complete
    GUI->>Database: Poll status
    Database-->>GUI: Job complete
    GUI-->>User: Video ready
```

---

## 🔐 Environment Variables

Required in `.env`:

```bash
# LLM Providers
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key         # Optional
ANTHROPIC_API_KEY=your_key      # Optional

# Media APIs
HF_TOKEN=your_huggingface_token
PEXELS_API_KEY=your_key
PIXABAY_API_KEY=your_key

# Social Platforms
META_ACCESS_TOKEN=your_token
FACEBOOK_PAGE_ID=your_id
INSTAGRAM_ACCOUNT_ID=your_id

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/agencyos

# Local AI (Optional)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

---

## 📝 Code Style Guidelines

- **Python**: 3.10+ with type hints
- **Linting**: `ruff check .`
- **Type Checking**: `mypy .`
- **Docstrings**: Google style
- **Max function length**: 50 lines
- **Max file length**: 500 lines

---

## 🔄 Version History

| Version | Highlights |
|---------|------------|
| 3.0.0 | Desktop GUI (PyQt6), Plugin architecture, DI container |
| 2.x | Web UI (Streamlit), Basic AI engines |
| 1.x | CLI-only, Core video processing |

---

*Last updated: December 2024*
