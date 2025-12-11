"""
Visual Timeline for AgencyOS.

Drag-and-drop timeline using QGraphicsView for video editing workflow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ClipItem(QGraphicsRectItem):
    """A draggable clip representing an asset segment on the timeline."""

    def __init__(
        self,
        asset_path: str | None = None,
        duration: float = 3.0,
        clip_type: str = "visual",
        width_per_sec: int = 60,
        clip_id: str = "",
    ) -> None:
        width = duration * width_per_sec
        height = 50
        super().__init__(0, 0, width, height)

        self.asset_path: str | None = asset_path
        self.duration: float = duration
        self.clip_type: str = clip_type
        self.width_per_sec: int = width_per_sec
        self.clip_id: str = clip_id or f"clip_{id(self)}"

        # Make draggable and selectable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        """Set visual style based on clip type."""
        colors: dict[str, QColor] = {
            "visual": QColor("#8b5cf6"),  # Purple for visuals
            "audio": QColor("#22c55e"),  # Green for audio
            "caption": QColor("#f59e0b"),  # Orange for captions
        }
        color = colors.get(self.clip_type, QColor("#64748b"))

        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120), 2))

        # Rounded corners effect via opacity
        self.setOpacity(0.9)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """Constrain movement to horizontal only within track."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            # Keep Y fixed (stay in lane)
            new_pos.setY(self.pos().y())
            # Don't go before time 0
            if new_pos.x() < 0:
                new_pos.setX(0)
            return new_pos
        return super().itemChange(change, value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize clip to dictionary."""
        return {
            "clip_id": self.clip_id,
            "asset_path": self.asset_path,
            "duration": self.duration,
            "clip_type": self.clip_type,
            "x_pos": self.pos().x(),
            "y_pos": self.pos().y(),
        }


class TimelineTrack(QGraphicsRectItem):
    """A horizontal track/lane for a specific asset type."""

    def __init__(self, y_pos: float, width: float, height: float, label: str) -> None:
        super().__init__(0, y_pos, width, height)
        self.label: str = label
        self.clips: list[ClipItem] = []

        # Track background
        self.setBrush(QBrush(QColor("#1e293b")))
        self.setPen(QPen(QColor("#334155"), 1))

    def add_clip(self, clip: ClipItem, x_pos: float = 0) -> None:
        """Add a clip to this track."""
        clip.setPos(x_pos, self.rect().y() + 5)
        self.clips.append(clip)

    def clear_clips(self) -> None:
        """Remove all clips from this track."""
        self.clips.clear()


class TimelineScene(QGraphicsScene):
    """The graphics scene containing all timeline elements."""

    clip_moved: pyqtSignal = pyqtSignal(object)  # Emitted when clip position changes

    def __init__(self, width: int = 2000, height: int = 200) -> None:
        super().__init__(0, 0, width, height)
        self.setBackgroundBrush(QBrush(QColor("#0f172a")))

        self.tracks: dict[str, TimelineTrack] = {}
        self._setup_tracks()
        self._add_time_ruler()

    def _setup_tracks(self) -> None:
        """Create the default tracks."""
        track_height = 60
        y_offset = 30  # Leave room for time ruler

        track_configs: list[tuple[str, str]] = [
            ("visual", "🎬 Visuals"),
            ("audio", "🎵 Audio"),
            ("caption", "💬 Captions"),
        ]

        for i, (track_id, label) in enumerate(track_configs):
            y_pos = y_offset + (i * track_height)
            track = TimelineTrack(y_pos, self.width(), track_height - 5, label)
            self.addItem(track)
            self.tracks[track_id] = track

    def _add_time_ruler(self) -> None:
        """Add time markers at the top."""
        pen = QPen(QColor("#475569"))
        text_color = QColor("#94a3b8")

        for sec in range(0, int(self.width() / 60) + 1):
            x = sec * 60
            # Tick mark
            self.addLine(x, 0, x, 20, pen)
            # Time label
            text = self.addText(f"{sec}s")
            text.setPos(x + 2, 2)
            text.setDefaultTextColor(text_color)

    def add_clip(
        self,
        track_id: str,
        duration: float,
        x_pos: float = 0,
        asset_path: str | None = None,
        clip_id: str = "",
    ) -> ClipItem | None:
        """Add a clip to the specified track."""
        if track_id not in self.tracks:
            return None

        clip = ClipItem(asset_path, duration, track_id, clip_id=clip_id)
        self.addItem(clip)
        self.tracks[track_id].add_clip(clip, x_pos)
        return clip

    def get_all_clips(self) -> list[ClipItem]:
        """Get all clips from all tracks."""
        clips: list[ClipItem] = []
        for track in self.tracks.values():
            clips.extend(track.clips)
        return clips

    def clear_all_clips(self) -> None:
        """Remove all clips from the scene."""
        for track in self.tracks.values():
            for clip in track.clips:
                self.removeItem(clip)
            track.clear_clips()


class TimelineView(QGraphicsView):
    """The main timeline widget."""

    def __init__(self) -> None:
        self.scene: TimelineScene = TimelineScene()
        super().__init__(self.scene)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure the view."""
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumHeight(220)

        # Style
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)

    def add_visual_clip(
        self, duration: float, x_pos: float = 0, clip_id: str = ""
    ) -> ClipItem | None:
        """Add a visual clip to the timeline."""
        return self.scene.add_clip("visual", duration, x_pos, clip_id=clip_id)

    def add_audio_clip(
        self, duration: float, x_pos: float = 0, clip_id: str = ""
    ) -> ClipItem | None:
        """Add an audio clip to the timeline."""
        return self.scene.add_clip("audio", duration, x_pos, clip_id=clip_id)

    def add_caption_clip(
        self, duration: float, x_pos: float = 0, clip_id: str = ""
    ) -> ClipItem | None:
        """Add a caption clip to the timeline."""
        return self.scene.add_clip("caption", duration, x_pos, clip_id=clip_id)


class TimelineWidget(QWidget):
    """Complete timeline widget with controls and save/load."""

    def __init__(self) -> None:
        super().__init__()
        self.timeline: TimelineView
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with controls
        header = QHBoxLayout()
        title = QLabel("🎬 Timeline")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e2e8f0;")
        header.addWidget(title)
        header.addStretch()

        # Save/Load buttons
        save_btn = QPushButton("💾")
        save_btn.setFixedSize(28, 28)
        save_btn.setToolTip("Save Timeline (Ctrl+S)")
        save_btn.setStyleSheet(self._btn_style())
        save_btn.clicked.connect(self._on_save_clicked)
        header.addWidget(save_btn)

        load_btn = QPushButton("📂")
        load_btn.setFixedSize(28, 28)
        load_btn.setToolTip("Load Timeline (Ctrl+O)")
        load_btn.setStyleSheet(self._btn_style())
        load_btn.clicked.connect(self._on_load_clicked)
        header.addWidget(load_btn)

        # Zoom controls
        zoom_out = QPushButton("−")
        zoom_out.setFixedSize(28, 28)
        zoom_out.setStyleSheet(self._btn_style())
        header.addWidget(zoom_out)

        zoom_in = QPushButton("+")
        zoom_in.setFixedSize(28, 28)
        zoom_in.setStyleSheet(self._btn_style())
        header.addWidget(zoom_in)

        layout.addLayout(header)

        # Timeline view
        self.timeline = TimelineView()
        layout.addWidget(self.timeline)

        # Connect zoom
        zoom_in.clicked.connect(lambda: self.timeline.scale(1.2, 1))
        zoom_out.clicked.connect(lambda: self.timeline.scale(0.8, 1))

    def _btn_style(self) -> str:
        return """
            QPushButton {
                background: #334155;
                border: none;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #475569;
            }
        """

    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Timeline", "", "JSON Files (*.json)"
        )
        if path:
            self.save_state(Path(path))

    def _on_load_clicked(self) -> None:
        """Handle load button click."""
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Load Timeline", "", "JSON Files (*.json)"
        )
        if path:
            self.load_state(Path(path))

    def add_demo_clips(self) -> None:
        """Add demo clips for testing."""
        self.timeline.add_visual_clip(3.0, 0)
        self.timeline.add_visual_clip(4.0, 200)
        self.timeline.add_visual_clip(2.5, 450)
        self.timeline.add_audio_clip(10.0, 0)
        self.timeline.add_caption_clip(2.0, 0)
        self.timeline.add_caption_clip(3.0, 150)

    def get_state(self) -> dict[str, Any]:
        """Get the current timeline state as a dictionary."""
        clips = self.timeline.scene.get_all_clips()
        return {
            "version": 1,
            "clips": [clip.to_dict() for clip in clips],
        }

    def save_state(self, path: Path) -> bool:
        """Save timeline state to a JSON file."""
        try:
            state = self.get_state()
            path.write_text(json.dumps(state, indent=2))
            return True
        except Exception:
            return False

    def load_state(self, path: Path) -> bool:
        """Load timeline state from a JSON file."""
        try:
            data = json.loads(path.read_text())
            if data.get("version") != 1:
                return False

            # Clear existing clips
            self.timeline.scene.clear_all_clips()

            # Load clips
            for clip_data in data.get("clips", []):
                track_id = clip_data.get("clip_type", "visual")
                self.timeline.scene.add_clip(
                    track_id=track_id,
                    duration=clip_data.get("duration", 3.0),
                    x_pos=clip_data.get("x_pos", 0),
                    asset_path=clip_data.get("asset_path"),
                    clip_id=clip_data.get("clip_id", ""),
                )
            return True
        except Exception:
            return False
