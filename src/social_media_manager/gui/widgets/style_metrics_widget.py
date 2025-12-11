"""
Style Metrics Widget for Brand Voice DNA Dashboard.

Displays visual representation of StyleTuner metrics:
- Progress bars for percentages (emoji usage, hashtag frequency)
- Gauges for scores (formality, vocabulary richness)
- Keyword chips for tone indicators
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class MetricProgressBar(QWidget):
    """A labeled progress bar for displaying percentage metrics."""

    def __init__(
        self,
        label: str,
        value: float = 0.0,
        max_value: float = 1.0,
        color: str = "#4CAF50",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._value = value
        self._max_value = max_value
        self._color = color
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label row
        label_row = QHBoxLayout()
        self.label_widget = QLabel(self._label)
        self.label_widget.setFont(QFont("Segoe UI", 10))

        self.value_label = QLabel(f"{self._value * 100:.0f}%")
        self.value_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        label_row.addWidget(self.label_widget)
        label_row.addWidget(self.value_label)
        layout.addLayout(label_row)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(int(self._value / self._max_value * 100))
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #3a3a3a;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {self._color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress)

    def set_value(self, value: float) -> None:
        """Update the displayed value."""
        self._value = value
        self.value_label.setText(f"{value * 100:.0f}%")
        self.progress.setValue(int(value / self._max_value * 100))


class FormalityGauge(QWidget):
    """A gauge widget showing formality score from Casual to Formal."""

    def __init__(self, value: float = 0.5, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value  # 0.0 = Casual, 1.0 = Formal
        self.setFixedHeight(60)
        self.setMinimumWidth(200)

    def set_value(self, value: float) -> None:
        """Update the formality value (0.0-1.0)."""
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the formality gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw track
        track_height = 8
        track_y = height // 2

        # Gradient from casual (yellow) to formal (blue)
        gradient_colors = ["#FFD54F", "#81C784", "#64B5F6"]
        segment_width = (width - 20) // 3

        for i, color in enumerate(gradient_colors):
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            x = 10 + i * segment_width
            w = segment_width if i < 2 else width - 20 - 2 * segment_width
            if i == 0:
                path = QPainterPath()
                path.addRoundedRect(
                    x, track_y - track_height // 2, w, track_height, 4, 4
                )
                painter.drawPath(path)
            elif i == 2:
                path = QPainterPath()
                path.addRoundedRect(
                    x, track_y - track_height // 2, w, track_height, 4, 4
                )
                painter.drawPath(path)
            else:
                painter.drawRect(x, track_y - track_height // 2, w, track_height)

        # Draw indicator
        indicator_x = 10 + (width - 20) * self._value
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#333333"), 2))
        painter.drawEllipse(int(indicator_x) - 8, track_y - 8, 16, 16)

        # Draw labels
        painter.setPen(QColor("#aaaaaa"))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.drawText(10, height - 5, "Casual")
        painter.drawText(width - 50, height - 5, "Formal")

        painter.end()


class KeywordChips(QWidget):
    """Widget displaying tone keywords as chips/tags."""

    def __init__(
        self, keywords: list[str] | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._keywords = keywords or []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.layout.addStretch()
        self._rebuild_chips()

    def _rebuild_chips(self) -> None:
        """Rebuild chip widgets from keywords."""
        # Clear existing chips (except stretch)
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for keyword in self._keywords[:5]:  # Limit to 5 chips
            chip = QLabel(keyword)
            chip.setFont(QFont("Segoe UI", 9))
            chip.setStyleSheet("""
                QLabel {
                    background-color: #4a4a6a;
                    color: #ffffff;
                    padding: 4px 10px;
                    border-radius: 12px;
                }
            """)
            self.layout.insertWidget(self.layout.count() - 1, chip)

    def set_keywords(self, keywords: list[str]) -> None:
        """Update displayed keywords."""
        self._keywords = keywords
        self._rebuild_chips()


class StyleMetricsWidget(QWidget):
    """
    Complete style metrics dashboard widget.

    Displays all StyleTuner metrics in a visually appealing format.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Title
        title = QLabel("📊 Style DNA Metrics")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Metrics grid
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        grid = QGridLayout(metrics_frame)
        grid.setSpacing(20)

        # Emoji Usage
        self.emoji_bar = MetricProgressBar("😀 Emoji Usage", 0.0, 1.0, "#FFD54F")
        grid.addWidget(self.emoji_bar, 0, 0)

        # Hashtag Frequency
        self.hashtag_bar = MetricProgressBar("# Hashtag Frequency", 0.0, 1.0, "#29B6F6")
        grid.addWidget(self.hashtag_bar, 0, 1)

        # Vocabulary Richness
        self.vocab_bar = MetricProgressBar(
            "📚 Vocabulary Richness", 0.0, 1.0, "#AB47BC"
        )
        grid.addWidget(self.vocab_bar, 1, 0)

        # Average Sentence Length indicator
        self.sentence_label = QLabel("📏 Avg Sentence Length: --")
        self.sentence_label.setFont(QFont("Segoe UI", 10))
        grid.addWidget(self.sentence_label, 1, 1)

        layout.addWidget(metrics_frame)

        # Formality Gauge
        formality_frame = QFrame()
        formality_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        formality_layout = QVBoxLayout(formality_frame)

        formality_title = QLabel("🎭 Formality Level")
        formality_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        formality_layout.addWidget(formality_title)

        self.formality_gauge = FormalityGauge()
        formality_layout.addWidget(self.formality_gauge)

        layout.addWidget(formality_frame)

        # Tone Keywords
        keywords_frame = QFrame()
        keywords_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        keywords_layout = QVBoxLayout(keywords_frame)

        keywords_title = QLabel("💬 Detected Tone Keywords")
        keywords_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        keywords_layout.addWidget(keywords_title)

        self.keyword_chips = KeywordChips()
        keywords_layout.addWidget(self.keyword_chips)

        layout.addWidget(keywords_frame)

        # Sample Count
        self.sample_count_label = QLabel("📝 Samples analyzed: 0")
        self.sample_count_label.setFont(QFont("Segoe UI", 10))
        self.sample_count_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.sample_count_label)

        layout.addStretch()

    def update_metrics(
        self,
        emoji_freq: float = 0.0,
        hashtag_freq: float = 0.0,
        vocab_richness: float = 0.0,
        avg_sentence_len: float = 0.0,
        formality: float = 0.5,
        tone_keywords: list[str] | None = None,
        sample_count: int = 0,
    ) -> None:
        """Update all metrics with new values from StyleTuner."""
        self.emoji_bar.set_value(min(emoji_freq, 1.0))
        self.hashtag_bar.set_value(min(hashtag_freq, 1.0))
        self.vocab_bar.set_value(min(vocab_richness, 1.0))
        self.sentence_label.setText(
            f"📏 Avg Sentence Length: {avg_sentence_len:.1f} words"
        )
        self.formality_gauge.set_value(formality)
        self.keyword_chips.set_keywords(tone_keywords or [])
        self.sample_count_label.setText(f"📝 Samples analyzed: {sample_count}")

    def clear_metrics(self) -> None:
        """Reset all metrics to default values."""
        self.update_metrics()
