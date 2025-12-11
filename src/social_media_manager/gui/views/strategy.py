"""
Strategy Room View for the Desktop GUI.

AI-powered strategic planning tools.
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...ai.brain import HybridBrain


class StrategyRoomView(QWidget):
    """Strategy Room for AI-powered planning."""

    def __init__(self):
        super().__init__()
        self._brain = None
        self._setup_ui()

    def _get_brain(self):
        if not self._brain:
            self._brain = HybridBrain()
        return self._brain

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎯 Strategy Room")
        title.setObjectName("h1")
        subtitle = QLabel("AI-powered strategic planning and analysis")
        subtitle.setObjectName("subtitle")

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()
        layout.addLayout(header)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_prompt_tab(), "🪄 Prompt Engineer")
        tabs.addTab(self._create_forecast_tab(), "📈 Engagement Forecast")
        tabs.addTab(self._create_trends_tab(), "📡 Trend Radar")
        tabs.addTab(self._create_focus_tab(), "🎭 Focus Group")
        layout.addWidget(tabs, 1)

    def _create_prompt_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Generate optimized prompts for AI image/video generation tools.")
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.concept_input = QLineEdit()
        self.concept_input.setPlaceholderText("Describe your content concept...")
        form.addRow("Concept:", self.concept_input)

        self.style_combo = QComboBox()
        self.style_combo.addItems(
            [
                "Photorealistic",
                "Cinematic",
                "Anime/Illustration",
                "3D Render",
                "Minimalist",
                "Vintage/Retro",
            ]
        )
        form.addRow("Style:", self.style_combo)

        self.target_combo = QComboBox()
        self.target_combo.addItems(
            [
                "Midjourney",
                "DALL-E",
                "Stable Diffusion",
                "Runway",
                "Pika Labs",
                "General",
            ]
        )
        form.addRow("Target AI:", self.target_combo)

        layout.addLayout(form)

        gen_btn = QPushButton("🪄 Generate Prompts")
        gen_btn.setObjectName("primary")
        gen_btn.clicked.connect(self._generate_prompts)
        layout.addWidget(gen_btn)

        self.prompt_output = QTextEdit()
        self.prompt_output.setReadOnly(True)
        self.prompt_output.setPlaceholderText("Generated prompts will appear here...")
        layout.addWidget(self.prompt_output, 1)

        return widget

    def _create_forecast_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Predict engagement for your content before publishing.")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        form_group = QGroupBox("Content Details")
        form = QFormLayout(form_group)

        self.content_type = QComboBox()
        self.content_type.addItems(
            ["Short Video", "Long Video", "Image Post", "Carousel", "Story"]
        )
        form.addRow("Content Type:", self.content_type)

        self.platform_forecast = QComboBox()
        self.platform_forecast.addItems(
            ["YouTube", "Instagram", "TikTok", "Twitter/X", "LinkedIn"]
        )
        form.addRow("Platform:", self.platform_forecast)

        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Main topic or niche...")
        form.addRow("Topic:", self.topic_input)

        self.hook_input = QLineEdit()
        self.hook_input.setPlaceholderText("Opening hook or headline...")
        form.addRow("Hook:", self.hook_input)

        layout.addWidget(form_group)

        forecast_btn = QPushButton("📊 Predict Engagement")
        forecast_btn.setObjectName("primary")
        forecast_btn.clicked.connect(self._run_forecast)
        layout.addWidget(forecast_btn)

        self.forecast_output = QTextEdit()
        self.forecast_output.setReadOnly(True)
        self.forecast_output.setPlaceholderText(
            "Engagement predictions will appear here..."
        )
        layout.addWidget(self.forecast_output, 1)

        return widget

    def _create_trends_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Scan for trending topics and viral content opportunities.")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        scan_row = QHBoxLayout()
        self.niche_input = QLineEdit()
        self.niche_input.setPlaceholderText(
            "Enter your niche (e.g., 'tech reviews', 'fitness')..."
        )
        scan_btn = QPushButton("📡 Scan Trends")
        scan_btn.setObjectName("primary")
        scan_btn.clicked.connect(self._scan_trends)
        scan_row.addWidget(self.niche_input, 1)
        scan_row.addWidget(scan_btn)
        layout.addLayout(scan_row)

        platform_row = QHBoxLayout()
        platform_row.addWidget(QLabel("Platforms:"))
        self.trends_platforms = QComboBox()
        self.trends_platforms.addItems(
            ["All", "YouTube", "TikTok", "Twitter/X", "Google Trends"]
        )
        platform_row.addWidget(self.trends_platforms, 1)
        platform_row.addStretch()
        layout.addLayout(platform_row)

        self.trends_output = QTextEdit()
        self.trends_output.setReadOnly(True)
        self.trends_output.setPlaceholderText("Trending topics will appear here...")
        layout.addWidget(self.trends_output, 1)

        return widget

    def _create_focus_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Simulate audience reactions with AI focus groups.")
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        form_group = QGroupBox("Content for Evaluation")
        form = QFormLayout(form_group)

        self.focus_content = QTextEdit()
        self.focus_content.setPlaceholderText(
            "Paste your script, caption, or content idea..."
        )
        self.focus_content.setMaximumHeight(120)
        form.addRow("Content:", self.focus_content)

        self.audience_input = QLineEdit()
        self.audience_input.setPlaceholderText("e.g., 'Gen Z tech enthusiasts'")
        form.addRow("Target Audience:", self.audience_input)

        self.group_size = QSpinBox()
        self.group_size.setRange(3, 12)
        self.group_size.setValue(5)
        form.addRow("Group Size:", self.group_size)

        layout.addWidget(form_group)

        run_btn = QPushButton("🎭 Run Focus Group")
        run_btn.setObjectName("primary")
        run_btn.clicked.connect(self._run_focus_group)
        layout.addWidget(run_btn)

        self.focus_output = QTextEdit()
        self.focus_output.setReadOnly(True)
        self.focus_output.setPlaceholderText("Focus group feedback will appear here...")
        layout.addWidget(self.focus_output, 1)

        return widget

    def _generate_prompts(self):
        concept = self.concept_input.text().strip()
        if not concept:
            QMessageBox.warning(self, "Error", "Please enter a concept first")
            return

        style = self.style_combo.currentText()
        target = self.target_combo.currentText()

        self.prompt_output.setText("⏳ Generating prompts...")

        try:
            result = self._get_brain().think(
                f"Generate 3 optimized {target} prompts for this concept:\n"
                f"Concept: {concept}\n"
                f"Style: {style}\n"
                f"Output each prompt on its own line with a number."
            )
            self.prompt_output.setText(result)
        except Exception as e:
            self.prompt_output.setText(f"Error: {e}")

    def _run_forecast(self):
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "Error", "Please enter topic details")
            return

        self.forecast_output.setText("⏳ Analyzing engagement potential...")

        try:
            result = self._get_brain().think(
                f"Predict engagement for this content:\n"
                f"Type: {self.content_type.currentText()}\n"
                f"Platform: {self.platform_forecast.currentText()}\n"
                f"Topic: {topic}\n"
                f"Hook: {self.hook_input.text()}\n\n"
                f"Provide: Expected engagement rate, best posting time, and improvement suggestions."
            )
            self.forecast_output.setText(result)
        except Exception as e:
            self.forecast_output.setText(f"Error: {e}")

    def _scan_trends(self):
        niche = self.niche_input.text().strip()
        if not niche:
            QMessageBox.warning(self, "Error", "Please enter a niche first")
            return

        self.trends_output.setText("📡 Scanning for trends...")

        try:
            from ...ai.radar import TrendRadar

            radar = TrendRadar()
            result = radar.check_trends(niche)

            if result:
                output = f"📡 Trending Topics for '{niche}':\n\n"
                output += f"🔥 Top Trend: {result.get('trend', 'N/A')}\n"
                output += f"📊 Score: {result.get('score', 'N/A')}\n"
                output += f"💡 Hook: {result.get('hook', 'N/A')}\n\n"

                if result.get("related"):
                    output += "📋 Related Trends:\n"
                    for t in result.get("related", [])[:5]:
                        output += f"  • {t}\n"

                if result.get("analysis"):
                    output += f"\n🧠 AI Analysis:\n{result.get('analysis')}"

                self.trends_output.setText(output)
            else:
                self.trends_output.setText(
                    f"⚠️ No trends found for '{niche}'.\n\n"
                    "Tips:\n"
                    "• Try a broader niche (e.g., 'Tech' instead of 'Tech AI')\n"
                    "• Make sure pytrends is installed: pip install pytrends\n"
                    "• Google Trends may be rate-limiting requests"
                )
        except Exception as e:
            self.trends_output.setText(f"❌ Error scanning trends:\n\n{e}")

    def _run_focus_group(self):
        content = self.focus_content.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Error", "Please enter content to evaluate")
            return

        self.focus_output.setText("🎭 Running focus group simulation...")

        try:
            audience = self.audience_input.text() or "general audience"
            size = self.group_size.value()

            result = self._get_brain().think(
                f"Simulate a focus group of {size} people from '{audience}'.\n"
                f"Evaluate this content:\n\n{content}\n\n"
                f"For each person, provide:\n"
                f"- Their persona (name, age, interests)\n"
                f"- Their reaction and feedback\n"
                f"- Rating out of 10\n\n"
                f"End with overall recommendations."
            )
            self.focus_output.setText(result)
        except Exception as e:
            self.focus_output.setText(f"Error: {e}")
