# 🚀 AgencyOS - AI Social Media Manager

**Version 3.0** — Desktop GUI Edition

A fully automated, AI-powered social media content creation and management platform. Create viral videos, generate AI content, and manage your social presence from one unified interface.

---

## ✨ Features

### 🧠 AI Brain (39 Engines)
- **LLM Integration**: Gemini, Groq, OpenRouter, Ollama, OpenAI, Anthropic
- **Content Generation**: Scripts, captions, hashtags, SEO optimization
- **Research**: Trend scanning, competitor analysis, engagement forecasting

### 🎬 Video Production
- **AI Avatars**: Talking head video generation
- **Music Composer**: AI-generated background music
- **Voice Synthesis**: VoxCPM text-to-speech with voice cloning
- **Video Processing**: Upscaling, background removal, face restoration

### 📊 Automation
- **Watch Folder**: Auto-process videos dropped into inbox
- **Batch Processing**: Queue multiple jobs
- **Job Queue**: Background task monitoring

### 🖥️ Desktop GUI
- Modern PyQt6 interface with 8 views
- 7 AI tool categories with 36+ tools
- Real-time system monitoring
- Dark theme with glassmorphism

---

## 📦 Installation

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (video processing)
- **GPU** (optional, for AI acceleration)

### Quick Start

```bash
# Clone repository
git clone https://github.com/youruser/social-media-manager.git
cd social-media-manager

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

---

## 🚀 Usage

### Launch Desktop GUI

```bash
python -m social_media_manager.gui.main
```

### Views
| View | Purpose |
|------|---------|
| 📊 Dashboard | Stats, activity feed, quick actions |
| 🎬 Content Studio | Script → Production workflow |
| 📚 Media Library | Visual search, video indexing |
| ⚡ Automation | Batch jobs, watch folders |
| 🎯 Strategy Room | Prompts, forecasting, trends |
| 🤖 AI Tools | 36+ AI tools in 7 categories |
| 📋 Job Queue | Background task monitor |
| ⚙️ Settings | API keys, LLM config |

---

## ⚙️ Configuration

Edit `.env` file:

```bash
# LLM Provider (gemini, groq, openai, ollama, etc.)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
LLM_FALLBACK_PROVIDER=groq
LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

# API Keys
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

---

## 🗂️ Project Structure

```
src/social_media_manager/
├── ai/              # 39 AI engines
├── automation/      # Watchdog, batch processing
├── core/            # Video/audio processors
├── gui/             # Desktop GUI (PyQt6)
│   ├── views/       # 8 main views
│   ├── widgets/     # Reusable components
│   └── styles.py    # Theme system
├── platforms/       # YouTube, Instagram APIs
├── database.py      # SQLite/PostgreSQL
└── job_queue.py     # Background workers
```

---

## 📖 Documentation

Full documentation available in the [`docs/`](docs/index.md) folder:

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/user-guide/getting-started.md) | Installation & first launch |
| [Configuration](docs/user-guide/configuration.md) | Complete `.env` reference |
| [GUI Views](docs/features/gui-views.md) | All 8 desktop views |
| [AI Tools](docs/features/ai-tools.md) | 45+ AI engines reference |
| [Automation](docs/features/automation.md) | Watch folders & batch processing |
| [Troubleshooting](docs/user-guide/troubleshooting.md) | Common issues & solutions |
| [Architecture](docs/development/architecture.md) | Developer overview |
| [Contributing](docs/development/contributing.md) | How to contribute |
| [Plugin Development](docs/PLUGINS.md) | Create custom tools |

---

## 📄 License

MIT License - See LICENSE file

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request
