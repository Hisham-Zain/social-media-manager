"""
Teleprompter View - Quick Recording Interface.

A simple, large-text view for recording ready-to-go scripts.
Part of the Trend-Jacking Autopilot - when a trend alert fires,
click through to this view and start recording immediately.
"""

from loguru import logger
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class TeleprompterView(QWidget):
    """
    Simple teleprompter for recording.

    Large scrolling text display with speed controls.
    Designed for quick recording after trend alerts.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._script: str = ""
        self._is_scrolling: bool = False
        self._scroll_speed: int = 50
        self._scroll_timer: QTimer | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Control bar
        control_bar = QFrame()
        control_bar.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                padding: 16px;
            }
        """)
        control_layout = QHBoxLayout(control_bar)

        # Title
        title = QLabel("📜 Teleprompter")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        control_layout.addWidget(title)

        control_layout.addStretch()

        # Speed control
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: #888888;")
        control_layout.addWidget(speed_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 100)
        self.speed_slider.setValue(50)
        self.speed_slider.setFixedWidth(150)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        control_layout.addWidget(self.speed_slider)

        # Font size
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #888888;")
        control_layout.addWidget(size_label)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(24, 96)
        self.size_spin.setValue(48)
        self.size_spin.valueChanged.connect(self._on_size_change)
        control_layout.addWidget(self.size_spin)

        # Play/Pause button
        self.play_btn = QPushButton("▶️ Start")
        self.play_btn.clicked.connect(self._toggle_scroll)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        control_layout.addWidget(self.play_btn)

        # Reset button
        reset_btn = QPushButton("↺ Reset")
        reset_btn.clicked.connect(self._reset_scroll)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
        """)
        control_layout.addWidget(reset_btn)

        layout.addWidget(control_bar)

        # Script display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #000000;
                border: none;
            }
        """)

        self.text_container = QWidget()
        self.text_container.setStyleSheet("background-color: #000000;")
        text_layout = QVBoxLayout(self.text_container)
        text_layout.setContentsMargins(100, 200, 100, 500)

        self.script_label = QLabel()
        self.script_label.setWordWrap(True)
        self.script_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_font()
        text_layout.addWidget(self.script_label)

        self.scroll_area.setWidget(self.text_container)
        layout.addWidget(self.scroll_area, 1)

        # Set up scroll timer
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._scroll_step)

    def _update_font(self) -> None:
        """Update the script font size."""
        size = self.size_spin.value() if hasattr(self, "size_spin") else 48
        self.script_label.setFont(QFont("Segoe UI", size))
        self.script_label.setStyleSheet(f"""
            color: white;
            font-size: {size}px;
            line-height: 1.5;
        """)

    def _on_speed_change(self, value: int) -> None:
        """Handle speed slider change."""
        self._scroll_speed = value
        # Restart timer with new speed if currently scrolling
        if self._is_scrolling and self._scroll_timer:
            self._scroll_timer.stop()
            self._scroll_timer.start(110 - value)

    def _on_size_change(self, value: int) -> None:
        """Handle font size change."""
        self._update_font()

    def _toggle_scroll(self) -> None:
        """Toggle auto-scroll."""
        if self._is_scrolling:
            self._stop_scroll()
        else:
            self._start_scroll()

    def _start_scroll(self) -> None:
        """Start auto-scrolling."""
        self._is_scrolling = True
        self.play_btn.setText("⏸️ Pause")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        if self._scroll_timer:
            self._scroll_timer.start(110 - self._scroll_speed)

    def _stop_scroll(self) -> None:
        """Stop auto-scrolling."""
        self._is_scrolling = False
        self.play_btn.setText("▶️ Start")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        if self._scroll_timer:
            self._scroll_timer.stop()

    def _scroll_step(self) -> None:
        """Single scroll step."""
        scrollbar = self.scroll_area.verticalScrollBar()
        current = scrollbar.value()
        scrollbar.setValue(current + 2)

        # Stop at end
        if current >= scrollbar.maximum():
            self._stop_scroll()

    def _reset_scroll(self) -> None:
        """Reset scroll to top."""
        self._stop_scroll()
        self.scroll_area.verticalScrollBar().setValue(0)

    def load_script(self, script: str, title: str = "") -> None:
        """
        Load a script into the teleprompter.

        Args:
            script: The script text to display.
            title: Optional title to show at the top.
        """
        self._script = script
        display_text = ""

        if title:
            display_text = f"<h1>{title}</h1><br><br>"

        # Format script for display
        paragraphs = script.split("\n\n")
        for para in paragraphs:
            display_text += f"<p>{para}</p><br>"

        self.script_label.setText(display_text)
        self._reset_scroll()
        logger.info(f"📜 Script loaded: {len(script)} chars")

    def set_script(self, script: str) -> None:
        """Load script without title."""
        self.load_script(script)
