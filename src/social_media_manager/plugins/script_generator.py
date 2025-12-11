"""
Script Generator Plugin - Example AI Tool Plugin.

Demonstrates the plugin architecture by implementing
a script generation tool as a standalone plugin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import BaseToolPlugin, PluginMetadata

if TYPE_CHECKING:
    pass


class ScriptGeneratorPlugin(BaseToolPlugin):
    """
    Plugin for AI-powered script generation.

    Generates viral video scripts based on user input topics.
    """

    metadata = PluginMetadata(
        name="Script Generator",
        description="Generate viral video scripts with AI",
        icon="📝",
        category="writing",
        version="1.0.0",
        author="AgencyOS",
    )

    def __init__(self) -> None:
        super().__init__()
        self._input: QTextEdit | None = None
        self._output: QTextEdit | None = None

    def get_widget(self) -> QWidget:
        """Create and return the plugin's UI widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Title
        title = QLabel("📝 Script Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e2e8f0;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Enter a topic or outline to generate a viral video script.")
        desc.setStyleSheet("color: #94a3b8;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Input
        self._input = QTextEdit()
        self._input.setPlaceholderText("Enter topic, outline, or key points...")
        self._input.setMaximumHeight(100)
        self._input.setStyleSheet("""
            QTextEdit {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
                color: #e2e8f0;
            }
        """)
        layout.addWidget(self._input)

        # Generate button
        btn = QPushButton("🚀 Generate Script")
        btn.setCursor(widget.cursor())
        btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #667eea, #764ba2);
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #764ba2, #667eea);
            }
        """)
        btn.clicked.connect(self._on_generate)
        layout.addWidget(btn)

        # Output
        self._output = QTextEdit()
        self._output.setPlaceholderText("Generated script will appear here...")
        self._output.setReadOnly(True)
        self._output.setStyleSheet("""
            QTextEdit {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
                color: #e2e8f0;
                font-family: monospace;
            }
        """)
        layout.addWidget(self._output)

        layout.addStretch()
        return widget

    def execute(self, topic: str = "", **kwargs: Any) -> dict[str, Any]:
        """
        Generate a script using AI.

        Args:
            topic: The topic or outline for the script.

        Returns:
            Dictionary with generated script.
        """
        try:
            from ..container import get_container

            container = get_container()
            brain = container.brain

            prompt = f"""Generate a viral video script about: {topic}

Requirements:
- Hook in first 3 seconds
- Clear structure (intro, body, CTA)
- Engaging and conversational tone
- 60-90 seconds when spoken

Format the script with:
[HOOK] - Opening hook
[INTRO] - Brief introduction
[MAIN] - Main content points
[CTA] - Call to action"""

            script = brain.think(prompt)
            self.log(f"Generated script for topic: {topic[:50]}...")

            return {"success": True, "script": script}

        except Exception as e:
            self.log(f"Error generating script: {e}")
            return {"success": False, "error": str(e)}

    def _on_generate(self) -> None:
        """Handle generate button click."""
        if not self._input or not self._output:
            return

        topic = self._input.toPlainText().strip()
        if not topic:
            self._output.setText("Please enter a topic first.")
            return

        self._output.setText("Generating script...")

        result = self.execute(topic=topic)

        if result.get("success"):
            self._output.setText(result.get("script", ""))
        else:
            self._output.setText(f"Error: {result.get('error', 'Unknown error')}")
