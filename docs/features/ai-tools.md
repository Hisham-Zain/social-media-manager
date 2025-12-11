# 🤖 AI Tools Reference

Complete documentation for all 45+ AI engines in AgencyOS.

---

## ✍️ Writing Tools

### Script Generator
**Generate video scripts from topics or outlines.**

| Parameter | Description |
|-----------|-------------|
| Topic | Main subject of the video |
| Style | Informative, entertaining, educational |
| Length | Short (30s), Medium (1-3m), Long (5m+) |
| Tone | Professional, casual, humorous |

```
Input: "Benefits of morning exercise"
Output: Hook, main points, CTA, with timestamps
```

---

### SEO Agent
**Optimize content for search and discovery.**

Features:
- Title optimization with keywords
- Description generation
- Tag suggestions
- Thumbnail text recommendations

---

### Caption Writer
**Generate engaging captions for posts.**

Platforms supported:
- Instagram (2200 chars)
- Twitter/X (280 chars)
- LinkedIn (3000 chars)
- TikTok (150 chars)

---

### Hashtag Generator
**AI-powered hashtag research.**

Returns:
- High-volume hashtags
- Niche-specific tags
- Trending hashtags
- Difficulty scores

---

### Newsroom
**Generate news-style content from sources.**

Scans trending topics and generates:
- News summaries
- Hot takes
- Commentary scripts

---

### Campaign Planner
**Multi-post campaign strategy.**

Creates:
- Content calendar
- Post series
- Cross-platform strategy
- A/B test variants

---

## 🎤 Audio Tools

### Text-to-Speech (VoxCPM)
**High-quality voice synthesis.**

| Voice | Description |
|-------|-------------|
| Default | Neutral English |
| Custom | Clone your voice |

Parameters:
- Speed (0.5x - 2.0x)
- Pitch adjustment
- Emotion (neutral, happy, serious)

---

### Voice Cloner
**Clone voices from audio samples.**

Requirements:
- 30+ seconds of clean audio
- Minimal background noise
- Consistent speaking style

---

### Music Composer
**AI-generated background music.**

Genres:
- Upbeat
- Cinematic
- Lo-fi
- Corporate
- Dramatic

Duration: 15s to 5m

---

### Transcriber
**Speech-to-text with timestamps.**

Outputs:
- Plain text
- SRT subtitles
- VTT captions
- Word-level timestamps

---

### Dubber
**Translate and dub videos.**

Languages:
- English, Spanish, French, German
- Japanese, Korean, Chinese
- Portuguese, Italian, Arabic

---

## 🎨 Visual Tools

### Upscaler
**Enhance video/image resolution.**

Scales:
- 2x (HD → 2K)
- 4x (HD → 4K)

Models: Real-ESRGAN, GFPGAN

---

### Face Restore
**Fix low-quality faces in videos.**

Uses GFPGAN for:
- Face enhancement
- Artifact removal
- Deblurring

---

### Background Remover
**Remove backgrounds from video/images.**

Modes:
- Person detection
- Chroma key
- AI segmentation

Output: Transparent PNG/WebM

---

### Style Graph
**Apply artistic styles to content.**

Styles:
- Cinematic color grading
- Anime/cartoon
- Vintage film
- Custom LUT

---

## 🎬 Video Tools

### AI Director
**Automated video editing decisions.**

Generates Edit Decision List (EDL):
- Scene cuts
- Transitions
- B-roll placement
- Music sync points

---

### Avatar Generator
**AI talking head videos.**

Options:
- Character selection
- Background settings
- Lip-sync from audio
- Expression control

---

### Video Producer
**Full production pipeline.**

Pipeline:
1. Script → Storyboard
2. Voice generation
3. Visual assembly
4. B-roll insertion
5. Music + effects
6. Final render

---

### Viral Cloner
**Analyze and replicate viral content patterns.**

Analyzes:
- Hook patterns
- Pacing
- Visual styles
- Audio trends

---

## 🔍 Research Tools

### Trend Radar
**Real-time trend monitoring.**

Sources:
- YouTube Trending
- Twitter/X trending topics
- Google Trends
- Reddit Hot

---

### Hunter
**Find high-performing content in niches.**

Metrics:
- View velocity
- Engagement rate
- Share rate
- Comment sentiment

---

### Forecaster
**Predict content performance.**

Inputs:
- Topic
- Platform
- Posting time

Outputs:
- Predicted views
- Engagement estimate
- Best posting time

---

### Analyzer
**Deep content analysis.**

Analyzes:
- Script structure
- Pacing
- Hook effectiveness
- CTA strength

---

## 🕵️ Intel Tools

### Browser Spy
**Automated web research.**

Features:
- Stealth browsing
- Content extraction
- Screenshot capture
- Data collection

---

### Searcher
**AI-powered web search.**

Integrates:
- Google search
- DuckDuckGo
- Perplexity AI
- Custom sources

---

### Visual RAG
**Video content search and retrieval.**

Indexes videos for:
- Scene search
- Object detection
- Similar frame finding
- Semantic search

---

### Competitor Spy
**Track competitor content.**

Monitors:
- Upload frequency
- Engagement patterns
- Content themes
- Growth trends

---

## 📤 Publish Tools

### Scheduler
**Cross-platform scheduling.**

Platforms:
- YouTube
- Instagram
- TikTok
- Twitter/X
- LinkedIn

Features:
- Best time suggestions
- Queue management
- Bulk scheduling

---

### Platform Uploader
**Direct publishing.**

Supports:
- Video upload
- Metadata setting
- Thumbnail upload
- Playlist assignment

---

### A/B Optimizer
**Test content variations.**

Tests:
- Thumbnails
- Titles
- Descriptions
- Posting times

---

## 🔌 Plugins

Custom tools created via the plugin system.

See [Plugin Development Guide](../PLUGINS.md) for creating custom tools.

---

## Tips

> [!TIP]
> **Chain tools for workflows**: Script Generator → TTS → Video Producer → Scheduler

> [!NOTE]
> Most tools run as background jobs. Monitor progress in the **Job Queue** view.
