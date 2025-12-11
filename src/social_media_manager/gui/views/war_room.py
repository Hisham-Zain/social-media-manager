"""
War Room View - Agent Debate Interface.

A chat-like interface where AI personas debate content strategies.
The user watches as Hype Beast, Skeptic, and Strategist argue
to produce a battle-tested final recommendation.
"""

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...ai.moderator import DebateMessage, DebateModerator, DebateResult
from ...ai.personas import HYPE_BEAST, SKEPTIC, STRATEGIST, Persona
from ..widgets.toasts import show_toast


class DebateWorker(QThread):
    """Background worker for running debates."""

    message_received = pyqtSignal(object)  # Emits DebateMessage
    finished = pyqtSignal(object)  # Emits DebateResult
    error = pyqtSignal(str)

    def __init__(self, moderator: DebateModerator, topic: str, rounds: int = 1) -> None:
        super().__init__()
        self.moderator = moderator
        self.topic = topic
        self.rounds = rounds

    def run(self) -> None:
        try:
            result = self.moderator.run_debate(
                topic=self.topic,
                rounds=self.rounds,
                on_message=lambda msg: self.message_received.emit(msg),
            )
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Debate failed: {e}")
            self.error.emit(str(e))


class MessageBubble(QFrame):
    """Chat bubble for a debate message."""

    def __init__(self, message: DebateMessage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._message = message
        self._setup_ui()

    def _setup_ui(self) -> None:
        persona = self._message.speaker
        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {persona.color}22;
                border-left: 4px solid {persona.color};
                border-radius: 8px;
                margin: 8px 0;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header: Avatar + Name + Round
        header = QHBoxLayout()

        avatar = QLabel(persona.avatar_emoji)
        avatar.setFont(QFont("Segoe UI", 20))
        header.addWidget(avatar)

        name = QLabel(f"<b>{persona.name}</b>")
        name.setStyleSheet(f"color: {persona.color}; font-size: 13px;")
        header.addWidget(name)

        round_label = QLabel(f"Round {self._message.round_number}")
        round_label.setStyleSheet("color: #888888; font-size: 10px;")
        header.addWidget(round_label)

        header.addStretch()
        layout.addLayout(header)

        # Content
        content = QLabel(self._message.content)
        content.setWordWrap(True)
        content.setStyleSheet("color: #e0e0e0; font-size: 12px; padding: 8px 0;")
        layout.addWidget(content)


class WarRoomView(QWidget):
    """
    War Room: AI Persona Debate Interface.

    Users input a topic and watch as three AI personas debate:
    1. Hype Beast - Opens with viral-focused take
    2. Skeptic - Critiques from credibility angle
    3. Strategist - Synthesizes final recommendation

    This creates value through productive disagreement.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._moderator: DebateModerator | None = None
        self._worker: DebateWorker | None = None
        self._current_result: DebateResult | None = None
        self._setup_ui()

    def _get_moderator(self) -> DebateModerator:
        """Lazy-load the debate moderator."""
        if self._moderator is None:
            self._moderator = DebateModerator()
        return self._moderator

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("🎭 War Room")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)

        subtitle = QLabel("Agent Debate Chamber")
        subtitle.setStyleSheet("color: #888888; font-size: 14px; padding-left: 8px;")
        header.addWidget(subtitle)

        header.addStretch()
        layout.addLayout(header)

        # Persona cards
        personas_layout = QHBoxLayout()
        for persona in [HYPE_BEAST, SKEPTIC, STRATEGIST]:
            card = self._create_persona_card(persona)
            personas_layout.addWidget(card)
        layout.addLayout(personas_layout)

        # Topic input
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)

        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(
            "Enter a topic to debate (e.g., 'AI ethics video for LinkedIn')..."
        )
        self.topic_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 12px;
                color: white;
                font-size: 14px;
            }
        """)
        self.topic_input.returnPressed.connect(self._start_debate)
        input_layout.addWidget(self.topic_input, 1)

        rounds_label = QLabel("Rounds:")
        rounds_label.setStyleSheet("color: #888888;")
        input_layout.addWidget(rounds_label)

        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 5)
        self.rounds_spin.setValue(1)
        self.rounds_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px;
                color: white;
            }
        """)
        input_layout.addWidget(self.rounds_spin)

        self.start_btn = QPushButton("⚔️ Start Debate")
        self.start_btn.clicked.connect(self._start_debate)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF8555;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666666;
            }
        """)
        input_layout.addWidget(self.start_btn)

        layout.addWidget(input_frame)

        # Debate scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(0)
        self.messages_layout.addStretch()

        scroll.setWidget(self.messages_container)
        layout.addWidget(scroll, 1)

        # Status bar
        self.status_label = QLabel("Enter a topic and start the debate...")
        self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Actions
        actions = QHBoxLayout()
        actions.addStretch()

        self.export_btn = QPushButton("📄 Export Transcript")
        self.export_btn.clicked.connect(self._export_transcript)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5a5a7a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)
        actions.addWidget(self.export_btn)

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self._clear_messages)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: white;
            }
        """)
        actions.addWidget(self.clear_btn)

        layout.addLayout(actions)

    def _create_persona_card(self, persona: Persona) -> QFrame:
        """Create a small card showing a persona."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {persona.color}22;
                border: 1px solid {persona.color}44;
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        emoji = QLabel(persona.avatar_emoji)
        emoji.setFont(QFont("Segoe UI", 18))
        header.addWidget(emoji)

        name = QLabel(f"<b>{persona.name}</b>")
        name.setStyleSheet(f"color: {persona.color}; font-size: 12px;")
        header.addWidget(name)
        header.addStretch()
        layout.addLayout(header)

        desc = QLabel(persona.critique_style.replace("_", " ").title())
        desc.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(desc)

        return card

    def _start_debate(self) -> None:
        """Start a new debate."""
        topic = self.topic_input.text().strip()
        if not topic:
            show_toast(self, "Please enter a topic to debate", "warning")
            return

        self._clear_messages()
        self.start_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.status_label.setText("🎭 Debate in progress...")

        rounds = self.rounds_spin.value()
        self._worker = DebateWorker(self._get_moderator(), topic, rounds)
        self._worker.message_received.connect(self._on_message)
        self._worker.finished.connect(self._on_debate_complete)
        self._worker.error.connect(self._on_debate_error)
        self._worker.start()

    def _on_message(self, message: DebateMessage) -> None:
        """Handle incoming debate message."""
        bubble = MessageBubble(message)
        # Insert before stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.status_label.setText(f"💬 {message.speaker.name} is speaking...")

    def _on_debate_complete(self, result: DebateResult) -> None:
        """Handle debate completion."""
        self._current_result = result
        self.start_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.status_label.setText(
            f"✅ Debate complete! {len(result.messages)} messages in "
            f"{result.duration_seconds:.1f}s"
        )
        show_toast(self, "Debate complete! Final recommendation ready.", "success")

    def _on_debate_error(self, error: str) -> None:
        """Handle debate error."""
        self.start_btn.setEnabled(True)
        self.status_label.setText(f"❌ Debate failed: {error}")
        show_toast(self, f"Debate failed: {error}", "error")

    def _clear_messages(self) -> None:
        """Clear all message bubbles."""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_result = None
        self.export_btn.setEnabled(False)

    def _export_transcript(self) -> None:
        """Export the debate transcript."""
        if not self._current_result:
            return

        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Debate Transcript",
            f"war_room_{self._current_result.topic[:30]}.md",
            "Markdown (*.md);;All Files (*)",
        )

        if path:
            md = self._get_moderator().export_debate_md(self._current_result)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            show_toast(self, f"Transcript exported: {path}", "success")
