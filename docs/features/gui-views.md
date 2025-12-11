# 🖥️ GUI Views Reference

AgencyOS features 8 main views accessible from the sidebar. Each view is designed for specific workflows.

---

## 📊 Dashboard

**The command center for your content operations.**

### Features
- **Stats Overview** — Videos created, scheduled, processing
- **Activity Feed** — Recent actions and completions
- **Quick Actions** — One-click access to common tasks
- **System Monitor** — CPU, RAM, GPU usage

### Quick Actions
| Action | Description |
|--------|-------------|
| New Script | Open Script Generator |
| Process Video | Quick video processing |
| Schedule Post | Open scheduling dialog |

---

## 🎬 Content Studio

**End-to-end video production workflow.**

### Workflow
1. **Script** — Write or generate with AI
2. **Storyboard** — AI generates visual plan (EDL)
3. **Assets** — Add B-roll, music, voiceover
4. **Preview** — Real-time video preview
5. **Export** — Render final video

### Components
- **Script Editor** — Rich text with AI suggestions
- **Timeline** — Drag-and-drop clip arrangement
- **Asset Browser** — Search stock + local media
- **Teleprompter** — Scrolling script display

---

## 📚 Media Library

**Visual asset management with AI search.**

### Features
- **Grid View** — Thumbnail gallery
- **Visual Search** — Find similar images/videos
- **Auto-Tagging** — AI-generated metadata
- **Collections** — Organize by project

### Supported Formats
- **Video**: MP4, MOV, AVI, MKV, WebM
- **Image**: PNG, JPG, WebP, GIF
- **Audio**: MP3, WAV, FLAC, AAC

---

## ⚡ Automation

**Batch processing and automated workflows.**

### Watch Folder
Drop videos into `~/social_media_manager/inbox/` for auto-processing.

Configure processing presets:
- Upscale → Background Remove → Caption → Export

### Batch Jobs
- Process multiple videos with same settings
- Queue management with priority
- Progress tracking

---

## 🎯 Strategy Room

**Content planning and trend analysis.**

### Features
- **Prompt Library** — Saved AI prompts
- **Trend Radar** — Real-time trend monitoring
- **Content Calendar** — Schedule visualization
- **Engagement Forecaster** — Predict performance

### Trend Sources
- YouTube Trending
- Twitter/X Topics
- Google Trends
- Reddit Hot Posts

---

## 🤖 AI Tools

**Direct access to all 45+ AI engines.**

Organized in 8 category tabs:

| Tab | Tools Count | Purpose |
|-----|-------------|---------|
| ✍️ Writing | 6 | Scripts, SEO, captions |
| 🎤 Audio | 5 | TTS, voice clone, music |
| 🎨 Visual | 4 | Upscale, restore, remove BG |
| 🎬 Video | 4 | Direction, avatars, production |
| 🔍 Research | 4 | Trends, analysis, forecasting |
| 🕵️ Intel | 4 | Web search, competitor spy |
| 📤 Publish | 3 | Scheduling, uploading |
| 🔌 Plugins | Dynamic | Custom tools |

See [AI Tools Reference](ai-tools.md) for complete documentation.

---

## 📋 Job Queue

**Background task monitoring.**

### Job States
| State | Icon | Description |
|-------|------|-------------|
| Pending | ⏳ | Waiting in queue |
| Running | 🔄 | Currently processing |
| Completed | ✅ | Successfully finished |
| Failed | ❌ | Error occurred |

### Actions
- **Retry** — Re-run failed jobs
- **Cancel** — Stop running jobs
- **Clear** — Remove completed jobs
- **Priority** — Drag to reorder

---

## ⚙️ Settings

**Application configuration.**

### Sections

#### 🧠 LLM Configuration
- Provider selection (Gemini, Groq, Ollama, etc.)
- Model selection
- API key management
- Test connection

#### 🔑 API Keys
- Secure storage for all service keys
- Connection status indicators
- Quick links to get keys

#### 📁 Paths
- Output directories
- Watch folder location
- Cache settings

#### 🎨 Appearance
- Theme (Dark/Light)
- Font size
- Accent color

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New project |
| `Ctrl+S` | Save |
| `Ctrl+G` | Generate (AI action) |
| `Ctrl+P` | Preview |
| `Ctrl+E` | Export |
| `Ctrl+1-8` | Switch views |
| `Escape` | Close dialog |
| `F11` | Toggle fullscreen |
