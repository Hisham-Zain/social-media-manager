# 🚀 Getting Started with AgencyOS

This guide will help you install and launch AgencyOS for the first time.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | [Download](https://python.org/downloads) |
| **FFmpeg** | Latest | Required for video processing |
| **GPU** | Optional | CUDA for accelerated AI inference |

### Install FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/youruser/social-media-manager.git
cd social-media-manager
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your API keys. See [Configuration Guide](configuration.md) for details.

**Minimum required keys:**
- `GEMINI_API_KEY` or `GROQ_API_KEY` — For AI text generation

---

## Launch the Application

```bash
# Option 1: Direct Python
python -m social_media_manager.gui.main

# Option 2: Launch script
./launch_gui.sh
```

The desktop GUI will open with the Dashboard view.

---

## First Steps

### 1. Configure LLM Provider

1. Go to **⚙️ Settings** → **LLM Configuration**
2. Select your preferred provider (Gemini, Groq, Ollama, etc.)
3. Enter your API key
4. Click **Test Connection**

### 2. Generate Your First Script

1. Go to **🤖 AI Tools** → **✍️ Writing** tab
2. Click **Script Generator**
3. Enter a topic and click **Generate**

### 3. Create a Video

1. Go to **🎬 Content Studio**
2. Paste your script or generate one
3. Click **Generate Storyboard**
4. Add visuals and music
5. Export to video

---

## Folder Structure

AgencyOS creates the following folders in `~/.social_media_manager/`:

| Folder | Purpose |
|--------|---------|
| `processed/` | Completed videos |
| `generated/` | AI-generated content |
| `assets/` | Uploaded media files |
| `music/` | Background music library |
| `thumbnails/` | Video thumbnails |

---

## Next Steps

- [Configuration Guide](configuration.md) — Full environment variable reference
- [GUI Views](../features/gui-views.md) — Explore all 8 views
- [AI Tools](../features/ai-tools.md) — Discover 45+ AI engines
