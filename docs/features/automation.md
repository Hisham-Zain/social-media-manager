# ⚡ Automation Guide

Automate your content production with watch folders, batch processing, and scheduled jobs.

---

## Watch Folder

**Automatic file processing**

Drop files into the watch folder for auto-processing:

```
~/social_media_manager/inbox/
```

### How It Works
1. Drop video/image files into `inbox/`
2. AgencyOS detects new files
3. Applies configured processing preset
4. Moves completed files to `processed/`

### Configuration

Enable watch folder in **⚙️ Settings** → **Automation**:

| Setting | Description |
|---------|-------------|
| Watch Folder | Enable/disable monitoring |
| Input Path | Folder to monitor |
| Output Path | Destination for processed files |
| Preset | Processing steps to apply |

### Processing Presets

| Preset | Steps |
|--------|-------|
| Quick Enhance | Upscale → Color correct |
| Full Production | Transcribe → Caption → Music → Export |
| Social Ready | Resize → Upscale → Optimize |

---

## Batch Processing

**Process multiple files at once**

### Steps
1. Go to **⚡ Automation** view
2. Click **Add Files** or drag-drop
3. Select processing preset
4. Click **Start Batch**

### Batch Options
- **Parallel Jobs**: Process 1-4 files simultaneously
- **Priority**: Order files by importance
- **Skip Errors**: Continue on failure

---

## Job Queue

**Background task management**

All processing runs in the background queue.

### Job Types
| Type | Description |
|------|-------------|
| `video_process` | Video rendering |
| `tts_generate` | Voice synthesis |
| `transcribe` | Speech-to-text |
| `upscale` | Resolution enhancement |
| `script_generate` | AI script writing |
| `upload` | Platform publishing |

### Job Lifecycle

```
PENDING → RUNNING → COMPLETED
                  ↘ FAILED → RETRY
```

### Managing Jobs

| Action | Keyboard | Description |
|--------|----------|-------------|
| Retry | `R` | Re-run failed job |
| Cancel | `Delete` | Stop running job |
| Priority Up | `↑` | Move up in queue |
| Priority Down | `↓` | Move down in queue |

---

## Scheduled Tasks

### Content Calendar

Schedule posts in **🎯 Strategy Room** → **Calendar**:

1. Create content
2. Click **Schedule**
3. Select date/time
4. Choose platforms
5. Confirm

### Best Time Suggestions

AgencyOS suggests optimal posting times based on:
- Historical engagement data
- Platform-specific patterns
- Audience timezone analysis

---

## Webhooks

**Trigger external actions on events**

Configure in **⚙️ Settings** → **Webhooks**:

| Event | Trigger |
|-------|---------|
| `job.completed` | Job finishes |
| `video.processed` | Video ready |
| `post.scheduled` | Content scheduled |
| `post.published` | Content goes live |

### Webhook Payload

```json
{
  "event": "job.completed",
  "timestamp": "2025-12-10T14:30:00Z",
  "data": {
    "job_id": "abc123",
    "type": "video_process",
    "status": "completed",
    "output_path": "/path/to/video.mp4"
  }
}
```

---

## Tips

> [!TIP]
> Use **watch folders** for hands-free processing of recurring content.

> [!NOTE]
> GPU acceleration significantly speeds up video processing. Check **Dashboard** for GPU status.
