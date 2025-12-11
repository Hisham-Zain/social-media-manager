"""
Embedded Media Player for AgencyOS.

QMediaPlayer widget for previewing generated videos.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# Try to import multimedia (may not be installed)
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget

    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


class MediaPlayerWidget(QWidget):
    """Embedded video player with controls."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if not MULTIMEDIA_AVAILABLE:
            # Fallback message
            fallback = QLabel(
                "📹 Media Player unavailable\n\n"
                "Install PyQt6-QtMultimedia:\n"
                "pip install PyQt6-QtMultimedia"
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("""
                background: #1e293b;
                color: #94a3b8;
                border-radius: 8px;
                padding: 40px;
                font-size: 14px;
            """)
            layout.addWidget(fallback)
            return

        # Video display
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 225)
        self.video_widget.setStyleSheet("background: #0f172a; border-radius: 8px;")
        layout.addWidget(self.video_widget, 1)

        # Media player
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)

        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)

        # Controls container
        controls = QWidget()
        controls.setStyleSheet("background: #1e293b; border-radius: 8px;")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(12, 8, 12, 8)

        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.sliderMoved.connect(self._seek)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #334155;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8b5cf6;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #8b5cf6;
                border-radius: 3px;
            }
        """)
        controls_layout.addWidget(self.seek_slider)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # Time display
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        btn_row.addWidget(self.time_label)

        btn_row.addStretch()

        # Playback controls
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setStyleSheet(self._button_style())
        btn_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(36, 36)
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setStyleSheet(self._button_style())
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()

        # Volume
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: #94a3b8;")
        btn_row.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self._set_volume)
        self.volume_slider.setStyleSheet(self.seek_slider.styleSheet())
        btn_row.addWidget(self.volume_slider)

        controls_layout.addLayout(btn_row)
        layout.addWidget(controls)

        # Set initial volume
        self.audio.setVolume(0.7)

    def _button_style(self) -> str:
        return """
            QPushButton {
                background: #334155;
                border: none;
                border-radius: 18px;
                color: #e2e8f0;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #8b5cf6;
            }
        """

    def load_video(self, path: str | Path) -> None:
        """Load a video file."""
        if not MULTIMEDIA_AVAILABLE:
            return
        self.player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self) -> None:
        """Start playback."""
        if MULTIMEDIA_AVAILABLE:
            self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        if MULTIMEDIA_AVAILABLE:
            self.player.pause()

    def _toggle_play(self) -> None:
        if not MULTIMEDIA_AVAILABLE:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _stop(self) -> None:
        if MULTIMEDIA_AVAILABLE:
            self.player.stop()

    def _seek(self, position: int) -> None:
        if MULTIMEDIA_AVAILABLE:
            self.player.setPosition(position)

    def _set_volume(self, value: int) -> None:
        if MULTIMEDIA_AVAILABLE:
            self.audio.setVolume(value / 100)

    def _on_position_changed(self, position: int) -> None:
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        self._update_time_label()

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, duration)
        self._update_time_label()

    def _on_state_changed(self, state: "QMediaPlayer.PlaybackState") -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def _update_time_label(self) -> None:
        if not MULTIMEDIA_AVAILABLE:
            return
        pos = self.player.position() // 1000
        dur = self.player.duration() // 1000
        self.time_label.setText(
            f"{pos // 60}:{pos % 60:02d} / {dur // 60}:{dur % 60:02d}"
        )
