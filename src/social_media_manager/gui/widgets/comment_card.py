"""
Comment Card Widget for Unified Engagement Inbox.

Displays a single comment with:
- Author info and platform icon
- Comment text with sentiment indicator
- AI-generated reply options
- Action buttons (Reply/Ignore)
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Platform icons mapping
PLATFORM_ICONS = {
    "youtube": "📺",
    "instagram": "📷",
    "linkedin": "💼",
    "tiktok": "🎵",
    "twitter": "🐦",
    "facebook": "📘",
}

# Sentiment colors
SENTIMENT_COLORS = {
    "positive": "#4CAF50",
    "neutral": "#FFC107",
    "negative": "#F44336",
}


class SentimentBadge(QLabel):
    """Small badge showing comment sentiment."""

    def __init__(
        self, sentiment: str = "neutral", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._sentiment = sentiment
        self._update_style()

    def _update_style(self) -> None:
        color = SENTIMENT_COLORS.get(self._sentiment, SENTIMENT_COLORS["neutral"])
        emoji = {"positive": "😊", "neutral": "😐", "negative": "😠"}.get(
            self._sentiment, "😐"
        )
        self.setText(emoji)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color}33;
                border: 1px solid {color};
                border-radius: 8px;
                padding: 2px 6px;
                font-size: 12px;
            }}
        """)

    def set_sentiment(self, sentiment: str) -> None:
        """Update the sentiment indicator."""
        self._sentiment = sentiment
        self._update_style()


class ReplyButton(QPushButton):
    """Styled button for AI reply options."""

    def __init__(self, text: str, tone: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.tone = tone
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Color based on tone
        colors = {
            "grateful": ("#4CAF50", "#388E3C"),
            "witty": ("#FF9800", "#F57C00"),
            "professional": ("#2196F3", "#1976D2"),
        }
        bg, hover = colors.get(tone, ("#666666", "#888888"))

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {bg};
            }}
        """)


class CommentCard(QFrame):
    """
    Card widget displaying a single comment with reply options.

    Signals:
        reply_selected: Emitted when user selects an AI reply (comment_id, reply_text)
        reply_custom: Emitted when user wants to write custom reply (comment_id)
        ignored: Emitted when user ignores the comment (comment_id)
    """

    reply_selected = pyqtSignal(int, str)  # comment_id, reply_text
    reply_custom = pyqtSignal(int)  # comment_id
    ignored = pyqtSignal(int)  # comment_id

    def __init__(
        self,
        comment_id: int,
        author: str,
        text: str,
        platform: str,
        timestamp: str = "",
        sentiment: str = "neutral",
        status: str = "pending",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.comment_id = comment_id
        self._author = author
        self._text = text
        self._platform = platform
        self._timestamp = timestamp
        self._sentiment = sentiment
        self._status = status
        self._reply_options: dict[str, str] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CommentCard {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            CommentCard:hover {
                border-color: #4a4a4a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Header row: Platform icon, Author, Timestamp, Sentiment
        header = QHBoxLayout()
        header.setSpacing(8)

        platform_icon = QLabel(PLATFORM_ICONS.get(self._platform.lower(), "💬"))
        platform_icon.setFont(QFont("Segoe UI", 16))
        header.addWidget(platform_icon)

        author_label = QLabel(f"<b>{self._author}</b>")
        author_label.setFont(QFont("Segoe UI", 11))
        header.addWidget(author_label)

        if self._timestamp:
            time_label = QLabel(f"• {self._timestamp}")
            time_label.setStyleSheet("color: #888888; font-size: 10px;")
            header.addWidget(time_label)

        header.addStretch()

        self.sentiment_badge = SentimentBadge(self._sentiment)
        header.addWidget(self.sentiment_badge)

        # Status badge
        self.status_label = QLabel(self._status.upper())
        status_colors = {
            "pending": "#FFC107",
            "replied": "#4CAF50",
            "ignored": "#888888",
        }
        color = status_colors.get(self._status, "#888888")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}33;
                color: {color};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # Comment text
        text_label = QLabel(self._text)
        text_label.setWordWrap(True)
        text_label.setFont(QFont("Segoe UI", 11))
        text_label.setStyleSheet("color: #e0e0e0; padding: 8px 0;")
        layout.addWidget(text_label)

        # Reply options container (hidden until generated)
        self.reply_container = QWidget()
        reply_layout = QVBoxLayout(self.reply_container)
        reply_layout.setContentsMargins(0, 8, 0, 0)
        reply_layout.setSpacing(8)

        reply_header = QLabel("🤖 AI-Suggested Replies:")
        reply_header.setStyleSheet("color: #888888; font-size: 11px;")
        reply_layout.addWidget(reply_header)

        self.reply_buttons_layout = QHBoxLayout()
        self.reply_buttons_layout.setSpacing(8)
        reply_layout.addLayout(self.reply_buttons_layout)

        self.reply_preview = QTextEdit()
        self.reply_preview.setReadOnly(True)
        self.reply_preview.setMaximumHeight(60)
        self.reply_preview.setPlaceholderText("Click a tone to preview the reply...")
        self.reply_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                color: #cccccc;
                font-size: 11px;
            }
        """)
        reply_layout.addWidget(self.reply_preview)

        self.reply_container.setVisible(False)
        layout.addWidget(self.reply_container)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch()

        self.generate_btn = QPushButton("🤖 Generate Replies")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a5a7a;
            }
        """)
        actions.addWidget(self.generate_btn)

        self.send_btn = QPushButton("✅ Send Reply")
        self.send_btn.clicked.connect(self._on_send_clicked)
        self.send_btn.setVisible(False)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        actions.addWidget(self.send_btn)

        ignore_btn = QPushButton("⏭️ Ignore")
        ignore_btn.clicked.connect(lambda: self.ignored.emit(self.comment_id))
        ignore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: #ffffff;
            }
        """)
        actions.addWidget(ignore_btn)

        layout.addLayout(actions)

    def _on_generate_clicked(self) -> None:
        """Emit signal to request reply generation."""
        # This will be connected externally to trigger AI generation
        self.reply_custom.emit(self.comment_id)

    def _on_send_clicked(self) -> None:
        """Send the currently previewed reply."""
        reply_text = self.reply_preview.toPlainText()
        if reply_text:
            self.reply_selected.emit(self.comment_id, reply_text)

    def set_reply_options(self, options: dict[str, str]) -> None:
        """
        Display AI-generated reply options.

        Args:
            options: Dict of {tone: reply_text}, e.g. {"grateful": "Thank you!"}
        """
        self._reply_options = options

        # Clear existing buttons
        while self.reply_buttons_layout.count():
            item = self.reply_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new buttons
        for tone, reply_text in options.items():
            btn = ReplyButton(tone.capitalize(), tone)
            btn.clicked.connect(lambda checked, t=tone: self._preview_reply(t))
            self.reply_buttons_layout.addWidget(btn)

        self.reply_buttons_layout.addStretch()
        self.reply_container.setVisible(True)
        self.generate_btn.setVisible(False)
        self.send_btn.setVisible(True)

    def _preview_reply(self, tone: str) -> None:
        """Preview a reply in the text area."""
        if tone in self._reply_options:
            self.reply_preview.setPlainText(self._reply_options[tone])

    def set_status(self, status: str) -> None:
        """Update the comment status."""
        self._status = status
        status_colors = {
            "pending": "#FFC107",
            "replied": "#4CAF50",
            "ignored": "#888888",
        }
        color = status_colors.get(status, "#888888")
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}33;
                color: {color};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
