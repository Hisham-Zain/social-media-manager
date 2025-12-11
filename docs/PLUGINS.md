# Plugin Development Guide

Create custom AI tools by implementing the `ToolPlugin` protocol.

## Quick Start

```python
# plugins/my_tool.py
from social_media_manager.plugins import BaseToolPlugin, PluginMetadata

class MyToolPlugin(BaseToolPlugin):
    metadata = PluginMetadata(
        name="My Tool",
        description="Does something useful",
        icon="🔧",
        category="writing",  # writing, audio, visual, video, research
    )

    def get_widget(self):
        # Return PyQt6 widget for the UI
        from PyQt6.QtWidgets import QLabel
        return QLabel("Hello from my plugin!")

    def execute(self, **kwargs):
        # Core logic
        return {"success": True, "result": "done"}
```

## Plugin Structure

| Field | Required | Description |
|-------|----------|-------------|
| `metadata` | ✅ | Plugin info (name, icon, category) |
| `get_widget()` | ✅ | Returns PyQt6 widget for UI |
| `execute(**kwargs)` | ✅ | Main functionality |

## Categories

- `writing` - Text generation tools
- `audio` - TTS, voice cloning, music
- `visual` - Image processing
- `video` - Video production
- `research` - Trends, analytics

## Example: Full Plugin

See [script_generator.py](file:///home/hisham/social-media-manager/src/social_media_manager/plugins/script_generator.py) for a complete implementation.

## Testing

```bash
python -c "
from social_media_manager.plugins.loader import get_plugin_loader
plugins = get_plugin_loader().discover()
print([p.metadata.name for p in plugins])
"
```
