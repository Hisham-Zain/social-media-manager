# ⚙️ Configuration Guide

Complete reference for all AgencyOS configuration options. All settings are managed via environment variables in the `.env` file.

---

## Quick Setup

```bash
cp .env.example .env
# Edit .env with your preferred editor
```

---

## LLM Configuration

### Primary Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Primary LLM provider |
| `LLM_MODEL` | `gemini-2.0-flash-exp` | Model to use |

**Supported Providers:** `gemini`, `groq`, `openai`, `anthropic`, `ollama`, `cohere`

### Fallback Chain

AgencyOS automatically falls back if the primary provider fails:

```env
# Primary: Gemini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp

# Fallback 1: Groq
LLM_FALLBACK_PROVIDER=groq
LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

# Fallback 2: Ollama (local)
LLM_FALLBACK2_PROVIDER=ollama
LLM_FALLBACK2_MODEL=llama3.2:3b
```

---

## API Keys

### LLM Providers

| Variable | Get Key |
|----------|---------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) (Free) |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com/) |
| `COHERE_API_KEY` | [Cohere Dashboard](https://dashboard.cohere.com/api-keys) |
| `PERPLEXITY_API_KEY` | [Perplexity Settings](https://www.perplexity.ai/settings/api) |

### Local LLM (Ollama)

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

> [!TIP]
> Install Ollama from [ollama.com](https://ollama.com) for free local inference.

### Media Generation

| Variable | Description | Get Key |
|----------|-------------|---------|
| `HF_TOKEN` | Hugging Face access | [HuggingFace Settings](https://huggingface.co/settings/tokens) |
| `PEXELS_API_KEY` | Stock photos | [Pexels API](https://www.pexels.com/api/) |
| `PIXABAY_API_KEY` | Stock media | [Pixabay API](https://pixabay.com/api/docs/) |

---

## Image & Video Generation

```env
# Options: huggingface, replicate
IMAGE_PROVIDER=huggingface
VIDEO_PROVIDER=huggingface
```

---

## Database Configuration

AgencyOS uses PostgreSQL for data storage.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agencyos

# Connection pool settings
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_ECHO=false  # Set true for SQL debugging
```

---

## Social Media Platforms

### YouTube

```env
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
```

### Instagram/Facebook

```env
INSTAGRAM_ACCESS_TOKEN=your_token
FACEBOOK_PAGE_ID=your_page_id
```

### TikTok

```env
TIKTOK_ACCESS_TOKEN=your_token
```

### LinkedIn

```env
LINKEDIN_ACCESS_TOKEN=your_token
```

---

## Remote Brain Server (Optional)

Run AI inference on a separate machine:

```env
USE_REMOTE_BRAIN=true
BRAIN_API_URL=http://your-server:8000
BRAIN_API_TIMEOUT=120
```

---

## MCP Integrations

```env
# Slack notifications
SLACK_TOKEN=xoxb-your-token
SLACK_CHANNEL=general

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS=path/to/credentials.json
```

---

## File Paths

All paths default to `~/.social_media_manager/`. Customize if needed:

| Directory | Purpose |
|-----------|---------|
| `BASE_DIR` | Root directory |
| `PROCESSED_DIR` | Completed videos |
| `GENERATED_DIR` | AI-generated content |
| `WATCH_FOLDER` | Auto-process inbox (default: `~/social_media_manager/inbox`) |
| `ASSETS_DIR` | Uploaded media |
| `MUSIC_DIR` | Background music |

---

## Example `.env`

```env
# === LLM ===
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
GEMINI_API_KEY=your_gemini_key

# === Fallback ===
LLM_FALLBACK_PROVIDER=groq
LLM_FALLBACK_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=your_groq_key

# === Media ===
IMAGE_PROVIDER=huggingface
HF_TOKEN=your_hf_token
PEXELS_API_KEY=your_pexels_key

# === Database ===
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agencyos
```
