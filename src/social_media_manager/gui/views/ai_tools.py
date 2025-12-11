"""
AI Tools Suite: Complete access to all AI engines.

Organized in tabbed categories for workflow-oriented access:
1. AI Writing - Scripts, SEO, Captions
2. Audio Lab - TTS, Voice Clone, Music
3. Visual Studio - Upscale, Face Restore, BG Remove
4. Video Production - Producer, Avatar, Director
5. Research & Intel - Trends, Competitors, Forecast
6. Content Intelligence - RAG, Memory, A/B Testing
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...job_queue import JobPriority, submit_job
from ...plugins.loader import get_plugin_loader

# =============================================================================
# REUSABLE COMPONENTS
# =============================================================================


class ModernToolCard(QWidget):
    """A sleek, clickable card for tool access."""

    def __init__(
        self, icon: str, title: str, desc: str, callback, color: str = "#667eea"
    ):
        super().__init__()
        self.callback = callback
        self.accent_color = color

        self.setStyleSheet(f"""
            ModernToolCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e2740, stop:1 #161d2f);
                border: 1px solid #2d3748;
                border-radius: 16px;
            }}
            ModernToolCard:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d3748, stop:1 #1e2740);
                border-color: {color};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Icon with accent background
        icon_container = QWidget()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {color}, stop:1 {self._darken_color(color)});
            border-radius: 14px;
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        icon_layout.addWidget(icon_lbl)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("""
            font-weight: 700;
            font-size: 16px;
            color: #ffffff;
            background: transparent;
        """)

        # Description
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("""
            color: #8892a6;
            font-size: 13px;
            background: transparent;
        """)

        layout.addWidget(icon_container)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()

    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color for gradient effect."""
        # Simple darkening - reduce RGB values
        hex_color = hex_color.lstrip("#")
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
        r, g, b = max(0, r - 40), max(0, g - 40), max(0, b - 40)
        return f"#{r:02x}{g:02x}{b:02x}"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback()


class ToolSection(QWidget):
    """A scrollable section containing tool cards in a grid."""

    def __init__(self, tools: list, columns: int = 3):
        super().__init__()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(20)
        grid.setContentsMargins(10, 10, 10, 10)

        row, col = 0, 0
        for icon, title, desc, callback, color in tools:
            card = ModernToolCard(icon, title, desc, callback, color)
            card.setMinimumSize(200, 160)
            card.setMaximumSize(280, 200)
            grid.addWidget(card, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

        # Add stretch to push cards to top-left
        grid.setRowStretch(row + 1, 1)
        grid.setColumnStretch(columns, 1)

        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)


# =============================================================================
# MAIN AI TOOLS VIEW
# =============================================================================


class AIToolsView(QWidget):
    """Complete AI Toolbox with all engines organized by category."""

    # Color palette for different categories
    COLORS = {
        "writing": "#667eea",  # Purple-blue
        "audio": "#48bb78",  # Green
        "visual": "#ed8936",  # Orange
        "video": "#e53e3e",  # Red
        "research": "#38b2ac",  # Teal
        "intel": "#9f7aea",  # Purple
        "publish": "#ec4899",  # Pink
    }

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("🤖 AI Toolbox")
        title.setObjectName("h1")
        subtitle = QLabel("All AI engines at your fingertips")
        subtitle.setObjectName("subtitle")

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        header.addLayout(header_text)
        header.addStretch()
        layout.addLayout(header)

        # Tabbed Categories
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2d3748;
                background: #0f111a;
                border-radius: 12px;
                padding: 10px;
            }
            QTabBar::tab {
                background: transparent;
                color: #718096;
                padding: 16px 28px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 15px;
            }
            QTabBar::tab:selected {
                background: #1a202c;
                color: #667eea;
                border-bottom: 3px solid #667eea;
            }
            QTabBar::tab:hover:!selected {
                background: #1a202c;
                color: #a0aec0;
            }
        """)

        # Add all category tabs
        self.tabs.addTab(self._create_writing_tab(), "✍️ AI Writing")
        self.tabs.addTab(self._create_audio_tab(), "🎵 Audio Lab")
        self.tabs.addTab(self._create_visual_tab(), "🖼️ Visual Studio")
        self.tabs.addTab(self._create_video_tab(), "🎬 Video Production")
        self.tabs.addTab(self._create_research_tab(), "📊 Research & Intel")
        self.tabs.addTab(self._create_intel_tab(), "🧠 Content Intelligence")
        self.tabs.addTab(self._create_publish_tab(), "🚀 Publish & Auth")
        self.tabs.addTab(self._create_plugins_tab(), "🔌 Plugins")

        layout.addWidget(self.tabs, 1)

    # =========================================================================
    # TAB 1: AI WRITING
    # =========================================================================

    def _create_writing_tab(self):
        color = self.COLORS["writing"]
        tools = [
            (
                "📝",
                "Script Generator",
                "AI-powered video scripts with hooks",
                self._tool_script,
                color,
            ),
            (
                "🔍",
                "SEO Optimizer",
                "Optimize content for search engines",
                self._tool_seo,
                color,
            ),
            (
                "💬",
                "Caption Writer",
                "Generate engaging social captions",
                self._tool_caption,
                color,
            ),
            (
                "#️⃣",
                "Hashtag Generator",
                "Research trending hashtags",
                self._tool_hashtags,
                color,
            ),
            (
                "📰",
                "Newsroom",
                "Generate news-style content",
                self._tool_newsroom,
                color,
            ),
            (
                "📋",
                "Campaign Architect",
                "Plan full marketing campaigns",
                self._tool_campaign,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 2: AUDIO LAB
    # =========================================================================

    def _create_audio_tab(self):
        color = self.COLORS["audio"]
        tools = [
            (
                "🗣️",
                "Text to Speech",
                "Convert text to natural speech",
                self._tool_tts,
                color,
            ),
            (
                "🎙️",
                "Voice Cloner",
                "Clone any voice from audio sample",
                self._tool_voice_clone,
                color,
            ),
            (
                "🎵",
                "Music Composer",
                "Generate background music",
                self._tool_music,
                color,
            ),
            (
                "🎤",
                "Transcriber",
                "Convert audio/video to text (Whisper)",
                self._tool_transcribe,
                color,
            ),
            (
                "🌍",
                "Content Dubber",
                "Dub content to other languages",
                self._tool_dubber,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 3: VISUAL STUDIO
    # =========================================================================

    def _create_visual_tab(self):
        color = self.COLORS["visual"]
        tools = [
            (
                "🖼️",
                "Image Upscaler",
                "Enhance images to 4K resolution",
                self._tool_upscale,
                color,
            ),
            (
                "👤",
                "Face Restorer",
                "Enhance and restore faces in photos",
                self._tool_face_restore,
                color,
            ),
            (
                "✂️",
                "Background Remover",
                "Remove backgrounds from images",
                self._tool_rembg,
                color,
            ),
            (
                "🎨",
                "Style Tuner",
                "Apply brand style to images",
                self._tool_style,
                color,
            ),
            ("📸", "Stock Hunter", "Find free stock images", self._tool_stock, color),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 4: VIDEO PRODUCTION
    # =========================================================================

    def _create_video_tab(self):
        color = self.COLORS["video"]
        tools = [
            (
                "🎬",
                "Video Producer",
                "Full automated video production",
                self._tool_producer,
                color,
            ),
            (
                "👤",
                "Avatar Engine",
                "Create talking head videos",
                self._tool_avatar,
                color,
            ),
            (
                "🎥",
                "Video Director",
                "AI-directed video editing",
                self._tool_director,
                color,
            ),
            (
                "♻️",
                "Content Repurposer",
                "Transform content for platforms",
                self._tool_repurpose,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 5: RESEARCH & INTEL
    # =========================================================================

    def _create_research_tab(self):
        color = self.COLORS["research"]
        tools = [
            (
                "📡",
                "Trend Radar",
                "Scan trending topics in real-time",
                self._tool_trends,
                color,
            ),
            (
                "🕵️",
                "Competitor Spy",
                "Analyze competitor strategies",
                self._tool_spy,
                color,
            ),
            (
                "🔮",
                "Trend Forecaster",
                "Predict upcoming trends",
                self._tool_forecast,
                color,
            ),
            (
                "📰",
                "Newsroom",
                "Monitor news for opportunities",
                self._tool_news_monitor,
                color,
            ),
            (
                "👁️",
                "Browser Spy",
                "Deep competitor web analysis",
                self._tool_browser_spy,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 6: CONTENT INTELLIGENCE
    # =========================================================================

    def _create_intel_tab(self):
        color = self.COLORS["intel"]
        tools = [
            (
                "👁️",
                "Visual RAG",
                "Search & index video content",
                self._tool_visual_rag,
                color,
            ),
            (
                "🧠",
                "Content Memory",
                "AI memory for content history",
                self._tool_memory,
                color,
            ),
            (
                "📚",
                "Smart Curator",
                "Curate content automatically",
                self._tool_curator,
                color,
            ),
            (
                "⚖️",
                "A/B Optimizer",
                "Optimize content with A/B testing",
                self._tool_ab_test,
                color,
            ),
            (
                "🤖",
                "Focus Group",
                "Digital focus group simulation",
                self._tool_focus_group,
                color,
            ),
            (
                "✅",
                "Content Critic",
                "AI critique of your content",
                self._tool_critic,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 7: PUBLISH & AUTH (CLI TOOLS)
    # =========================================================================

    def _create_publish_tab(self):
        color = self.COLORS["publish"]
        tools = [
            (
                "📤",
                "Upload Video",
                "Process and upload video to platforms",
                self._tool_upload,
                color,
            ),
            (
                "📊",
                "View Stats",
                "View analytics and performance metrics",
                self._tool_stats,
                color,
            ),
            (
                "🔑",
                "YouTube Auth",
                "Authenticate with YouTube (OAuth2)",
                self._tool_auth_youtube,
                color,
            ),
            (
                "📸",
                "Instagram Auth",
                "Verify Instagram credentials",
                self._tool_auth_instagram,
                color,
            ),
            (
                "🚀",
                "Start Watchdog",
                "Auto-process videos from watch folder",
                self._tool_watchdog,
                color,
            ),
        ]
        return ToolSection(tools)

    # =========================================================================
    # TAB 8: PLUGINS (Dynamic)
    # =========================================================================

    def _create_plugins_tab(self) -> QWidget:
        """Create the dynamic plugins tab that loads from PluginLoader."""
        loader = get_plugin_loader()
        plugins = loader.discover()

        if not plugins:
            # Show empty state
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(40, 40, 40, 40)

            empty_label = QLabel("🔌 No plugins installed")
            empty_label.setStyleSheet("font-size: 20px; color: #8892a6;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            hint_label = QLabel(
                "Add plugins to the plugins/ folder to extend functionality.\n"
                "Each plugin should implement the ToolPlugin protocol."
            )
            hint_label.setStyleSheet("color: #64748b; font-size: 14px;")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_label.setWordWrap(True)

            layout.addStretch()
            layout.addWidget(empty_label)
            layout.addWidget(hint_label)
            layout.addStretch()
            return widget

        # Create scrollable container for plugin widgets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Group plugins by category
        categories: dict[str, list] = {}
        for plugin in plugins:
            cat = plugin.metadata.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(plugin)

        # Render each category
        for category, cat_plugins in categories.items():
            # Category header
            cat_header = QLabel(f"📁 {category.title()}")
            cat_header.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #e2e8f0;
                padding: 8px 0;
            """)
            layout.addWidget(cat_header)

            # Plugin cards for this category
            for plugin in cat_plugins:
                widget = self._create_plugin_card(plugin)
                layout.addWidget(widget)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_plugin_card(self, plugin) -> QWidget:
        """Create a card widget for a single plugin."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: #1e2740;
                border: 1px solid #2d3748;
                border-radius: 12px;
            }
            QWidget:hover {
                border-color: #667eea;
            }
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel(plugin.metadata.icon)
        icon_label.setStyleSheet("""
            font-size: 28px;
            background: #667eea;
            border-radius: 10px;
            padding: 10px;
        """)
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = QLabel(plugin.metadata.name)
        name_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #e2e8f0; background: transparent;"
        )

        desc_label = QLabel(plugin.metadata.description)
        desc_label.setStyleSheet(
            "font-size: 13px; color: #8892a6; background: transparent;"
        )
        desc_label.setWordWrap(True)

        version_label = QLabel(
            f"v{plugin.metadata.version} by {plugin.metadata.author}"
        )
        version_label.setStyleSheet(
            "font-size: 12px; color: #64748b; background: transparent;"
        )

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        info_layout.addWidget(version_label)

        # Open button
        open_btn = QPushButton("Open")
        open_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #764ba2;
            }
        """)
        open_btn.clicked.connect(lambda checked, p=plugin: self._open_plugin(p))

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)
        layout.addWidget(open_btn)

        return card

    def _open_plugin(self, plugin) -> None:
        """Open a plugin in a dialog window."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{plugin.metadata.icon} {plugin.metadata.name}")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background: #0f111a;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Get the plugin's widget
        plugin_widget = plugin.get_widget()
        layout.addWidget(plugin_widget)

        dialog.exec()

    # =========================================================================
    # TOOL CALLBACKS - AI WRITING
    # =========================================================================

    def _tool_script(self):
        self._show_text_dialog(
            "📝 Script Generator",
            "Enter topic or idea for your video script:",
            "Generate a 60-second video script about: {input}",
            "script_generate",
        )

    def _tool_seo(self):
        self._show_input_dialog(
            "🔍 SEO Optimizer",
            [
                ("Content", "text"),
                ("Target Keywords", "text"),
            ],
            "seo_optimize",
        )

    def _tool_caption(self):
        self._show_input_dialog(
            "💬 Caption Writer",
            [
                ("Content/Topic", "text"),
                (
                    "Platform",
                    "combo",
                    ["Instagram", "Twitter/X", "LinkedIn", "TikTok", "Facebook"],
                ),
                (
                    "Tone",
                    "combo",
                    ["Professional", "Casual", "Humorous", "Inspirational"],
                ),
            ],
            "caption_write",
        )

    def _tool_hashtags(self):
        self._show_input_dialog(
            "# Hashtag Generator",
            [
                ("Topic/Niche", "text"),
                ("Platform", "combo", ["Instagram", "Twitter/X", "TikTok", "LinkedIn"]),
                ("Count", "spin", (5, 30, 15)),
            ],
            "hashtag_generate",
        )

    def _tool_newsroom(self):
        self._show_input_dialog(
            "📰 Newsroom",
            [
                ("Topic", "text"),
                (
                    "Style",
                    "combo",
                    ["Breaking News", "Feature Story", "Opinion", "Analysis"],
                ),
            ],
            "newsroom_generate",
        )

    def _tool_campaign(self):
        self._show_input_dialog(
            "📋 Campaign Architect",
            [
                ("Campaign Goal", "text"),
                ("Target Audience", "text"),
                ("Duration (days)", "spin", (7, 90, 30)),
            ],
            "campaign_plan",
        )

    # =========================================================================
    # TOOL CALLBACKS - AUDIO LAB
    # =========================================================================

    def _tool_tts(self):
        self._show_input_dialog(
            "🗣️ Text to Speech",
            [
                ("Text", "text"),
                (
                    "Voice",
                    "combo",
                    [
                        "en-US-AriaNeural",
                        "en-US-GuyNeural",
                        "en-GB-RyanNeural",
                        "en-US-JennyNeural",
                        "en-AU-NatashaNeural",
                    ],
                ),
                ("Speed", "combo", ["Normal", "Slow", "Fast"]),
            ],
            "tts_generate",
        )

    def _tool_voice_clone(self):
        self._show_file_dialog(
            "🎙️ Voice Cloner",
            [
                ("Reference Audio", "file", "Audio Files (*.mp3 *.wav *.m4a)"),
                ("Text to Speak", "text"),
            ],
            "voice_clone",
        )

    def _tool_music(self):
        self._show_input_dialog(
            "🎵 Music Composer",
            [
                (
                    "Style/Mood",
                    "combo",
                    [
                        "Corporate",
                        "Lofi",
                        "Cinematic",
                        "Upbeat",
                        "Ambient",
                        "Rock",
                        "Electronic",
                        "Jazz",
                    ],
                ),
                ("Duration (seconds)", "spin", (15, 180, 60)),
                ("Description", "text"),
            ],
            "music_compose",
        )

    def _tool_transcribe(self):
        self._show_file_dialog(
            "🎤 Transcriber",
            [
                (
                    "Audio/Video File",
                    "file",
                    "Media Files (*.mp3 *.wav *.mp4 *.mkv *.m4a)",
                ),
                (
                    "Language",
                    "combo",
                    ["Auto-detect", "English", "Spanish", "French", "German", "Arabic"],
                ),
            ],
            "transcribe",
        )

    def _tool_dubber(self):
        self._show_file_dialog(
            "🌍 Content Dubber",
            [
                ("Video File", "file", "Video Files (*.mp4 *.mkv *.mov)"),
                (
                    "Target Language",
                    "combo",
                    ["Spanish", "French", "German", "Arabic", "Mandarin", "Japanese"],
                ),
            ],
            "dub_content",
        )

    # =========================================================================
    # TOOL CALLBACKS - VISUAL STUDIO
    # =========================================================================

    def _tool_upscale(self):
        self._show_file_dialog(
            "🖼️ Image Upscaler",
            [
                ("Image", "file", "Images (*.png *.jpg *.jpeg *.webp)"),
                ("Scale Factor", "combo", ["2x", "4x"]),
            ],
            "upscale_image",
        )

    def _tool_face_restore(self):
        self._show_file_dialog(
            "👤 Face Restorer",
            [
                ("Image", "file", "Images (*.png *.jpg *.jpeg *.webp)"),
            ],
            "restore_face",
        )

    def _tool_rembg(self):
        self._show_file_dialog(
            "✂️ Background Remover",
            [
                ("Image", "file", "Images (*.png *.jpg *.jpeg *.webp)"),
            ],
            "remove_background",
        )

    def _tool_style(self):
        self._show_input_dialog(
            "🎨 Style Tuner",
            [
                ("Brand/Style Name", "text"),
                ("Description", "text"),
            ],
            "style_tune",
        )

    def _tool_stock(self):
        self._show_input_dialog(
            "📸 Stock Hunter",
            [
                ("Search Query", "text"),
                ("Orientation", "combo", ["Any", "Landscape", "Portrait", "Square"]),
                ("Count", "spin", (1, 20, 5)),
            ],
            "stock_search",
        )

    # =========================================================================
    # TOOL CALLBACKS - VIDEO PRODUCTION
    # =========================================================================

    def _tool_producer(self):
        self._show_input_dialog(
            "🎬 Video Producer",
            [
                ("Script", "text"),
                ("Style", "combo", ["News Anchor", "Casual", "Energetic", "Corporate"]),
                (
                    "Platform",
                    "combo",
                    ["YouTube (16:9)", "Shorts/TikTok (9:16)", "Instagram (1:1)"],
                ),
            ],
            "video_produce",
        )

    def _tool_avatar(self):
        self._show_file_dialog(
            "👤 Avatar Engine",
            [
                ("Avatar Image", "file", "Images (*.png *.jpg *.jpeg)"),
                ("Audio/Script", "text"),
                (
                    "Preset",
                    "combo",
                    ["News Anchor", "Casual", "Presenter", "Energetic"],
                ),
            ],
            "avatar_create",
        )

    def _tool_director(self):
        self._show_input_dialog(
            "🎥 Video Director",
            [
                ("Concept", "text"),
                ("Duration", "combo", ["15s", "30s", "60s", "90s"]),
                (
                    "Style",
                    "combo",
                    ["Documentary", "Commercial", "Social Media", "Tutorial"],
                ),
            ],
            "video_direct",
        )

    def _tool_repurpose(self):
        self._show_file_dialog(
            "♻️ Content Repurposer",
            [
                ("Source Content", "file", "All Files (*)"),
                (
                    "Target Format",
                    "combo",
                    [
                        "YouTube → Shorts",
                        "Podcast → Clips",
                        "Blog → Social",
                        "Video → GIF",
                    ],
                ),
            ],
            "repurpose_content",
        )

    # =========================================================================
    # TOOL CALLBACKS - RESEARCH & INTEL
    # =========================================================================

    def _tool_trends(self):
        self._show_input_dialog(
            "📡 Trend Radar",
            [
                ("Niche/Industry", "text"),
                (
                    "Platforms",
                    "combo",
                    ["All", "Twitter/X", "TikTok", "YouTube", "Instagram"],
                ),
            ],
            "scan_trends",
        )

    def _tool_spy(self):
        self._show_input_dialog(
            "🕵️ Competitor Spy",
            [
                ("Competitor Name/URL", "text"),
                (
                    "Analysis Depth",
                    "combo",
                    ["Quick Scan", "Standard", "Deep Analysis"],
                ),
            ],
            "spy_competitor",
        )

    def _tool_forecast(self):
        self._show_input_dialog(
            "🔮 Trend Forecaster",
            [
                ("Industry/Niche", "text"),
                ("Timeframe", "combo", ["Next Week", "Next Month", "Next Quarter"]),
            ],
            "forecast_trends",
        )

    def _tool_news_monitor(self):
        self._show_input_dialog(
            "📰 News Monitor",
            [
                ("Keywords", "text"),
                (
                    "Sources",
                    "combo",
                    ["All", "Tech", "Business", "Entertainment", "Custom"],
                ),
            ],
            "monitor_news",
        )

    def _tool_browser_spy(self):
        self._show_input_dialog(
            "👁️ Browser Spy",
            [
                ("Target URL", "text"),
                (
                    "Analysis Type",
                    "combo",
                    ["Content", "SEO", "Social Presence", "Full Audit"],
                ),
            ],
            "browser_spy",
        )

    # =========================================================================
    # TOOL CALLBACKS - CONTENT INTELLIGENCE
    # =========================================================================

    def _tool_visual_rag(self):
        self._show_file_dialog(
            "👁️ Visual RAG",
            [
                ("Video/Folder", "file", "Video Files (*.mp4 *.mkv *.mov)"),
                ("Action", "combo", ["Index New Content", "Search Existing"]),
            ],
            "visual_rag",
        )

    def _tool_memory(self):
        QMessageBox.information(
            self,
            "🧠 Content Memory",
            "Content Memory runs continuously to remember your content history.\n\n"
            "Access memories via the AI Writing tools for context-aware generation.",
        )

    def _tool_curator(self):
        self._show_input_dialog(
            "📚 Smart Curator",
            [
                ("Content Type", "combo", ["Articles", "Videos", "Images", "Mixed"]),
                ("Topic/Niche", "text"),
                ("Count", "spin", (5, 50, 10)),
            ],
            "curate_content",
        )

    def _tool_ab_test(self):
        self._show_input_dialog(
            "⚖️ A/B Optimizer",
            [
                ("Variant A", "text"),
                ("Variant B", "text"),
                ("Metric", "combo", ["Engagement", "Clicks", "Conversions"]),
            ],
            "ab_test",
        )

    def _tool_focus_group(self):
        self._show_input_dialog(
            "🤖 Focus Group",
            [
                ("Content/Concept", "text"),
                ("Target Demographic", "text"),
                ("Group Size", "spin", (3, 12, 5)),
            ],
            "focus_group",
        )

    def _tool_critic(self):
        self._show_text_dialog(
            "✅ Content Critic",
            "Paste your content for AI critique:",
            "{input}",
            "critique_content",
        )

    # =========================================================================
    # TOOL CALLBACKS - PUBLISH & AUTH
    # =========================================================================

    def _tool_upload(self):
        self._show_file_dialog(
            "📤 Upload Video",
            [
                ("Video File", "file", "Video Files (*.mp4 *.mkv *.mov *.avi)"),
                ("Platform", "combo", ["YouTube", "Instagram", "TikTok", "All"]),
            ],
            "video_process",
        )

    def _tool_stats(self):
        # Show stats in a dialog
        try:
            from ...database import DatabaseManager

            db = DatabaseManager()
            df = db.get_analytics()

            if df.empty:
                QMessageBox.information(
                    self,
                    "📊 Analytics",
                    "No analytics data available yet.\n\n"
                    "Upload some content first to see performance metrics.",
                )
            else:
                # Format stats summary
                stats_text = f"Total Posts: {len(df)}\n\n"
                for _, row in df.head(10).iterrows():
                    stats_text += (
                        f"• {row.get('platform', 'N/A')}: "
                        f"{row.get('views', 0)} views, "
                        f"{row.get('likes', 0)} likes\n"
                    )
                QMessageBox.information(self, "📊 Analytics", stats_text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load stats: {e}")

    def _tool_auth_youtube(self):
        QMessageBox.information(
            self,
            "🔑 YouTube Auth",
            "YouTube OAuth2 Authentication\n\n"
            "To authenticate with YouTube:\n\n"
            "1. Ensure 'creds/client_secrets.json' exists\n"
            "2. Run in terminal:\n"
            "   python -m social_media_manager auth youtube\n\n"
            "This will open a browser for Google OAuth.",
        )

    def _tool_auth_instagram(self):
        self._show_input_dialog(
            "📸 Instagram Auth",
            [
                ("Username", "text"),
                ("Password", "text"),
            ],
            "auth_instagram",
        )

    def _tool_watchdog(self):
        QMessageBox.information(
            self,
            "🚀 Watchdog",
            "Auto-Pilot Watchdog\n\n"
            "To start the watchdog that monitors your inbox folder:\n\n"
            "Run in terminal:\n"
            "   python -m social_media_manager start\n\n"
            "Or use the Automation Hub for more control.",
        )

    # =========================================================================
    # DIALOG HELPERS
    # =========================================================================

    def _show_input_dialog(self, title: str, fields: list, job_type: str):
        """Show input dialog with various field types."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(450)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a202c;
                color: white;
            }
            QLabel {
                color: #e2e8f0;
                font-weight: 500;
            }
            QLineEdit, QComboBox, QSpinBox {
                padding: 10px;
                background: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 6px;
                color: white;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #667eea;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
            }
        """)

        layout = QFormLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        inputs = {}
        for field_spec in fields:
            name = field_spec[0]
            field_type = field_spec[1]

            if field_type == "text":
                widget = QLineEdit()
                widget.setPlaceholderText(f"Enter {name.lower()}...")
            elif field_type == "combo":
                widget = QComboBox()
                widget.addItems(field_spec[2])
            elif field_type == "spin":
                widget = QSpinBox()
                min_val, max_val, default = field_spec[2]
                widget.setRange(min_val, max_val)
                widget.setValue(default)
            else:
                widget = QLineEdit()

            layout.addRow(f"{name}:", widget)
            inputs[name] = widget

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            payload = {}
            for name, widget in inputs.items():
                key = name.lower().replace(" ", "_").replace("/", "_")
                if isinstance(widget, QLineEdit):
                    payload[key] = widget.text()
                elif isinstance(widget, QComboBox):
                    payload[key] = widget.currentText()
                elif isinstance(widget, QSpinBox):
                    payload[key] = widget.value()

            job_id = submit_job(job_type, payload, JobPriority.NORMAL)
            QMessageBox.information(
                self,
                "✅ Job Started",
                f"Job submitted successfully!\n\nJob ID: {job_id[:12]}...\n\n"
                "Check the Job Queue tab for progress.",
            )

    def _show_file_dialog(self, title: str, fields: list, job_type: str):
        """Show dialog with file browser support."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a202c;
                color: white;
            }
            QLabel { color: #e2e8f0; font-weight: 500; }
            QLineEdit, QComboBox {
                padding: 10px; background: #2d3748;
                border: 1px solid #4a5568; border-radius: 6px; color: white;
            }
            QPushButton { padding: 8px 16px; border-radius: 6px; }
        """)

        layout = QFormLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        inputs = {}
        for field_spec in fields:
            name = field_spec[0]
            field_type = field_spec[1]

            if field_type == "file":
                row = QHBoxLayout()
                line_edit = QLineEdit()
                line_edit.setPlaceholderText("Select file...")
                browse_btn = QPushButton("Browse")
                file_filter = field_spec[2] if len(field_spec) > 2 else "All Files (*)"
                browse_btn.clicked.connect(
                    lambda checked, le=line_edit, ff=file_filter: self._browse_file(
                        le, ff
                    )
                )
                row.addWidget(line_edit, 1)
                row.addWidget(browse_btn)
                layout.addRow(f"{name}:", row)
                inputs[name] = line_edit
            elif field_type == "text":
                widget = QLineEdit()
                widget.setPlaceholderText(f"Enter {name.lower()}...")
                layout.addRow(f"{name}:", widget)
                inputs[name] = widget
            elif field_type == "combo":
                widget = QComboBox()
                widget.addItems(field_spec[2])
                layout.addRow(f"{name}:", widget)
                inputs[name] = widget

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec():
            payload = {}
            for name, widget in inputs.items():
                key = name.lower().replace(" ", "_").replace("/", "_")
                if isinstance(widget, QLineEdit):
                    payload[key] = widget.text()
                elif isinstance(widget, QComboBox):
                    payload[key] = widget.currentText()

            job_id = submit_job(job_type, payload, JobPriority.NORMAL)
            QMessageBox.information(
                self,
                "✅ Job Started",
                f"Job submitted successfully!\n\nJob ID: {job_id[:12]}...\n\n"
                "Check the Job Queue tab for progress.",
            )

    def _show_text_dialog(self, title: str, prompt: str, template: str, job_type: str):
        """Show dialog with large text input."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(500, 350)
        dialog.setStyleSheet("""
            QDialog { background-color: #1a202c; color: white; }
            QLabel { color: #e2e8f0; font-size: 14px; }
            QTextEdit {
                background: #2d3748; border: 1px solid #4a5568;
                border-radius: 8px; padding: 12px; color: white; font-size: 14px;
            }
            QPushButton { padding: 12px 24px; border-radius: 6px; font-weight: 600; }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        label = QLabel(prompt)
        layout.addWidget(label)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Type or paste your content here...")
        layout.addWidget(text_edit, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            content = text_edit.toPlainText()
            if content.strip():
                payload = {"content": content, "template": template}
                job_id = submit_job(job_type, payload, JobPriority.NORMAL)
                QMessageBox.information(
                    self,
                    "✅ Job Started",
                    f"Job submitted!\n\nJob ID: {job_id[:12]}...",
                )

    def _browse_file(self, line_edit: QLineEdit, file_filter: str):
        """Open file browser and set path to line edit."""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if path:
            line_edit.setText(path)
