"""
Modern Content Studio: The Production Workflow Engine.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...ai.brain import HybridBrain
from ...job_queue import JobPriority, submit_job
from ..widgets.media_player import MediaPlayerWidget
from ..widgets.timeline import TimelineWidget
from ..widgets.toasts import show_toast
from ..widgets.transcript_widget import TranscriptEditorWidget


class ContentStudioView(QWidget):
    def __init__(self):
        super().__init__()
        # Lazy load brain for UI responsiveness
        self.brain = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎬 Content Studio Pro")
        title.setObjectName("h1")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Main Workflow Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_ideation_tab(), "1. Ideation & Script")
        self.tabs.addTab(self._create_assets_tab(), "2. Assets & Style")
        self.tabs.addTab(self._create_production_tab(), "3. Production")
        self.tabs.addTab(self._create_timeline_tab(), "4. Timeline Editor")
        self.tabs.addTab(self._create_transcript_tab(), "5. Transcript Editor")

        layout.addWidget(self.tabs)

    def _create_ideation_tab(self):
        """Tab 1: Research trends, generate hooks, write script."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Topic & Trends
        row1 = QHBoxLayout()
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(
            "Enter a topic (e.g. 'AI Agents for Business')..."
        )

        trend_btn = QPushButton("📡 Scan Trends")
        trend_btn.clicked.connect(self._scan_trends)

        row1.addWidget(self.topic_input, 3)
        row1.addWidget(trend_btn, 1)
        layout.addLayout(row1)

        # Splitter for Hooks and Script
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Hooks
        hooks_group = QGroupBox("Viral Hooks")
        hooks_layout = QVBoxLayout(hooks_group)
        self.hooks_display = QTextEdit()
        self.hooks_display.setPlaceholderText("Generated hooks will appear here...")
        gen_hooks_btn = QPushButton("⚡ Generate Hooks")
        gen_hooks_btn.clicked.connect(self._generate_hooks)
        hooks_layout.addWidget(self.hooks_display)
        hooks_layout.addWidget(gen_hooks_btn)

        # Right: Script
        script_group = QGroupBox("Final Script")
        script_layout = QVBoxLayout(script_group)
        self.script_editor = QTextEdit()
        self.script_editor.setPlaceholderText(
            "Write or generate your full script here..."
        )

        script_actions = QHBoxLayout()
        write_btn = QPushButton("📝 Write Script")
        write_btn.clicked.connect(self._write_script)
        improve_btn = QPushButton("✨ Auto-Refine")
        improve_btn.clicked.connect(self._refine_script)

        script_actions.addWidget(write_btn)
        script_actions.addWidget(improve_btn)
        script_layout.addWidget(self.script_editor)
        script_layout.addLayout(script_actions)

        splitter.addWidget(hooks_group)
        splitter.addWidget(script_group)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        return widget

    def _create_assets_tab(self):
        """Tab 2: Configure Avatar, Voice, Music."""
        widget = QWidget()
        layout = QGridLayout(widget)

        # -- Avatar Settings --
        avatar_group = QGroupBox("👤 Avatar & Visuals")
        avatar_layout = QFormLayout(avatar_group)

        self.avatar_path = QLineEdit()
        self.avatar_path.setPlaceholderText("Path to avatar image...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_avatar)

        self.avatar_preset = QComboBox()
        self.avatar_preset.addItems(
            ["news_anchor", "casual", "energetic", "presentation"]
        )

        avatar_layout.addRow("Image:", self.avatar_path)
        avatar_layout.addRow("", browse_btn)
        avatar_layout.addRow("Preset:", self.avatar_preset)
        layout.addWidget(avatar_group, 0, 0)

        # -- Audio Settings --
        audio_group = QGroupBox("🎤 Audio & Voice")
        audio_layout = QFormLayout(audio_group)

        self.voice_select = QComboBox()
        self.voice_select.addItems(
            ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-RyanNeural"]
        )

        self.music_style = QComboBox()
        self.music_style.addItems(["corporate", "lofi", "cinematic", "rock", "upbeat"])

        audio_layout.addRow("Voice:", self.voice_select)
        audio_layout.addRow("Music Style:", self.music_style)
        layout.addWidget(audio_group, 0, 1)

        # -- Preview Area with Media Player --
        preview_group = QGroupBox("🎥 Media Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.media_player = MediaPlayerWidget()
        preview_layout.addWidget(self.media_player)

        layout.addWidget(preview_group, 1, 0, 1, 2)

        return widget

    def _create_production_tab(self):
        """Tab 3: Final render settings and Job submission."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        settings_group = QGroupBox("Render Settings")
        form = QFormLayout(settings_group)

        self.platform_select = QComboBox()
        self.platform_select.addItems(
            ["YouTube (16:9)", "Shorts/TikTok (9:16)", "Instagram (1:1)"]
        )

        self.quality_select = QComboBox()
        self.quality_select.addItems(["1080p", "4K (Upscaled)", "720p (Draft)"])

        self.priority_select = QComboBox()
        self.priority_select.addItems(["Normal", "High (Urgent)", "Low (Batch)"])

        form.addRow("Platform:", self.platform_select)
        form.addRow("Quality:", self.quality_select)
        form.addRow("Priority:", self.priority_select)
        layout.addWidget(settings_group)

        # Big Render Button
        self.render_btn = QPushButton("🚀 START PRODUCTION ENGINE")
        self.render_btn.setObjectName("primary")
        self.render_btn.setFixedHeight(50)
        self.render_btn.setStyleSheet("font-size: 16px; margin-top: 20px;")
        self.render_btn.clicked.connect(self._submit_job)
        layout.addWidget(self.render_btn)

        # Status
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setPlaceholderText("Job status will appear here...")
        layout.addWidget(self.status_log)

        return widget

    def _create_timeline_tab(self):
        """Tab 4: Visual timeline editor."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Timeline widget with demo clips
        self.timeline = TimelineWidget()
        self.timeline.add_demo_clips()
        layout.addWidget(self.timeline)

        # Instructions
        info = QLabel(
            "💡 Drag clips to reorder • Zoom with +/- • "
            "Purple = Visuals, Green = Audio, Orange = Captions"
        )
        info.setStyleSheet("color: #94a3b8; padding: 10px;")
        layout.addWidget(info)

        return widget

    def _create_transcript_tab(self):
        """Tab 5: Text-based video editing."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Transcript Editor widget
        self.transcript_editor = TranscriptEditorWidget()
        self.transcript_editor.video_exported.connect(self._on_video_exported)
        layout.addWidget(self.transcript_editor)

        return widget

    def _on_video_exported(self, path: str) -> None:
        """Handle exported video from transcript editor."""
        self.media_player.load_video(path)
        self.tabs.setCurrentIndex(1)  # Switch to Assets tab for preview
        show_toast(self, f"Video exported and loaded: {path}", "success")

    # --- Logic Methods ---

    def _get_brain(self):
        if not self.brain:
            self.brain = HybridBrain()
        return self.brain

    def _scan_trends(self):
        topic = self.topic_input.text()
        if not topic:
            show_toast(self, "Please enter a topic first", "warning")
            return
        self.hooks_display.setText(f"🔍 Scanning trends for '{topic}'...")

        try:
            from ...ai.radar import TrendRadar

            radar = TrendRadar()
            result = radar.check_trends(topic)

            if result:
                output = f"📡 Trending Topics for '{topic}':\n\n"
                output += f"🔥 Top Trend: {result.get('trend', 'N/A')}\n"
                output += f"📊 Score: {result.get('score', 'N/A')}\n"
                output += f"💡 Hook: {result.get('hook', 'N/A')}\n\n"

                if result.get("related"):
                    output += "📋 Related Trends:\n"
                    for t in result.get("related", [])[:5]:
                        output += f"  • {t}\n"

                self.hooks_display.setText(output)
                show_toast(self, f"Found trends for '{topic}'", "success")
            else:
                self.hooks_display.setText(
                    f"⚠️ No trends found for '{topic}'.\n\n"
                    "Try a broader topic or check if pytrends is installed."
                )
                show_toast(self, "No trends found", "warning")
        except Exception as e:
            self.hooks_display.setText(f"❌ Error scanning trends:\n\n{e}")
            show_toast(self, "Trend scan failed", "error")

    def _generate_hooks(self):
        topic = self.topic_input.text()
        if not topic:
            show_toast(self, "Please enter a topic first", "warning")
            return
        try:
            res = self._get_brain().generate_viral_hooks(topic)
            text = "\n\n".join(
                [f"{h['style']}: {h['text']}" for h in res.get("hooks", [])]
            )
            self.hooks_display.setText(text)
            show_toast(self, "Hooks generated!", "success")
        except Exception as e:
            self.hooks_display.setText(f"Error: {e}")
            show_toast(self, "Hook generation failed", "error")

    def _write_script(self):
        topic = self.topic_input.text()
        if not topic:
            show_toast(self, "Please enter a topic first", "warning")
            return
        try:
            script = self._get_brain().think(
                f"Write a 60s video script about {topic}. Include timestamps."
            )
            self.script_editor.setText(script)
            show_toast(self, "Script written!", "success")
        except Exception as e:
            self.script_editor.setText(f"Error: {e}")
            show_toast(self, "Script writing failed", "error")

    def _refine_script(self):
        current = self.script_editor.toPlainText()
        if not current:
            show_toast(self, "Please write a script first", "warning")
            return
        try:
            refined = self._get_brain().think(
                f"Refine this script to be more viral and concise:\n{current}"
            )
            self.script_editor.setText(refined)
            show_toast(self, "Script refined!", "success")
        except Exception as e:
            self.script_editor.setText(f"Error: {e}")
            show_toast(self, "Refinement failed", "error")

    def _browse_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Avatar Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.avatar_path.setText(path)
            show_toast(self, "Avatar selected", "success")

    def _submit_job(self):
        script = self.script_editor.toPlainText()
        if not script:
            show_toast(self, "Please write a script first", "warning")
            return

        payload = {
            "script": script,
            "avatar_image": self.avatar_path.text(),
            "voice": self.voice_select.currentText(),
            "music_style": self.music_style.currentText(),
            "platform": self.platform_select.currentText().split()[0].lower(),
            "name": f"Video_{self.topic_input.text()}",
        }

        job_id = submit_job("video_produce", payload, JobPriority.NORMAL)
        self.status_log.append(f"🚀 Job Submitted! ID: {job_id}")
        self.status_log.append("Monitor progress in the Job Queue tab.")
        show_toast(self, f"Job submitted: {job_id}", "success")

    def load_video_preview(self, path: str) -> None:
        """Load a video into the preview player."""
        self.media_player.load_video(path)
        show_toast(self, "Video loaded for preview", "info")
