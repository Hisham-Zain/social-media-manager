"""
Alchemy View - Content Transmutation Interface.

Drop a video and watch it transform into platform-native assets.
The "Magic" vibe: lead (raw video) → gold (10 optimized assets).
"""

from pathlib import Path

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...ai.alchemist import ContentAlchemist, TransmutationResult
from ...core.factory import AssetFactory
from ..widgets.toasts import show_toast


class TransmutationWorker(QThread):
    """Background worker for video transmutation."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # TransmutationResult
    error = pyqtSignal(str)

    def __init__(
        self,
        alchemist: ContentAlchemist,
        video_path: str,
        transcript: str,
    ) -> None:
        super().__init__()
        self.alchemist = alchemist
        self.video_path = video_path
        self.transcript = transcript

    def run(self) -> None:
        try:
            self.progress.emit("⚗️ Analyzing content...")
            result = self.alchemist.transmute(self.video_path, self.transcript)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Transmutation failed: {e}")
            self.error.emit(str(e))


class AssetBuildWorker(QThread):
    """Background worker for building assets."""

    progress = pyqtSignal(str, int)  # message, percent
    finished = pyqtSignal(list)  # List of GeneratedAsset
    error = pyqtSignal(str)

    def __init__(
        self,
        factory: AssetFactory,
        result: TransmutationResult,
    ) -> None:
        super().__init__()
        self.factory = factory
        self.result = result

    def run(self) -> None:
        try:
            all_assets = []

            # Build carousel
            self.progress.emit("🎨 Building LinkedIn carousel...", 20)
            carousel_texts = []
            for asset in self.result.assets:
                if asset.asset_type == "linkedin_carousel":
                    carousel_texts = asset.content
                    break
            if carousel_texts:
                carousel_assets = self.factory.build_carousel(carousel_texts)
                all_assets.extend(carousel_assets)

            # Save Twitter thread
            self.progress.emit("🐦 Saving Twitter thread...", 40)
            for asset in self.result.assets:
                if asset.asset_type == "twitter_thread":
                    thread_asset = self.factory.save_twitter_thread(asset.content)
                    all_assets.append(thread_asset)
                    break

            # Extract clips
            self.progress.emit("✂️ Extracting video clips...", 60)
            timestamps = []
            for asset in self.result.assets:
                if asset.timestamps:
                    timestamps.extend(asset.timestamps)
            if timestamps and self.result.source_video:
                clip_assets = self.factory.extract_clips(
                    self.result.source_video, timestamps
                )
                all_assets.extend(clip_assets)

            # Build quote graphic from controversial take
            self.progress.emit("💬 Creating quote graphic...", 80)
            if self.result.controversial_take:
                quote_asset = self.factory.build_quote_graphic(
                    self.result.controversial_take
                )
                if quote_asset:
                    all_assets.append(quote_asset)

            self.progress.emit("✅ Complete!", 100)
            self.finished.emit(all_assets)

        except Exception as e:
            logger.error(f"Asset building failed: {e}")
            self.error.emit(str(e))


class AlchemyView(QWidget):
    """
    Content Alchemy Engine Interface.

    Users drop a video file, the system transcribes it, then
    transmutes it into platform-native assets.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._alchemist: ContentAlchemist | None = None
        self._factory: AssetFactory | None = None
        self._current_result: TransmutationResult | None = None
        self._video_path: str = ""
        self._transcript: str = ""
        self._worker: TransmutationWorker | None = None
        self._build_worker: AssetBuildWorker | None = None
        self._setup_ui()

    def _get_alchemist(self) -> ContentAlchemist:
        if self._alchemist is None:
            self._alchemist = ContentAlchemist()
        return self._alchemist

    def _get_factory(self) -> AssetFactory:
        if self._factory is None:
            self._factory = AssetFactory()
        return self._factory

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("⚗️ Content Alchemy")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.addWidget(title)

        subtitle = QLabel("1 Video → 10 Assets")
        subtitle.setStyleSheet("color: #FFD700; font-size: 14px; padding-left: 8px;")
        header.addWidget(subtitle)

        header.addStretch()
        layout.addLayout(header)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Input panel
        left_panel = self._create_input_panel()
        splitter.addWidget(left_panel)

        # Right: Output tree
        right_panel = self._create_output_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter, 1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("Drop a video to begin transmutation...")
        self.status_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.status_label)

    def _create_input_panel(self) -> QWidget:
        """Create the input panel with video selection and transcript."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(panel)

        # Video selection
        video_group = QGroupBox("📹 Source Video")
        video_layout = QVBoxLayout(video_group)

        self.video_label = QLabel("No video selected")
        self.video_label.setStyleSheet("color: #888888;")
        video_layout.addWidget(self.video_label)

        select_btn = QPushButton("📁 Select Video")
        select_btn.clicked.connect(self._select_video)
        video_layout.addWidget(select_btn)

        layout.addWidget(video_group)

        # Transcript input
        transcript_group = QGroupBox("📝 Transcript")
        transcript_layout = QVBoxLayout(transcript_group)

        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(
            "Paste transcript here, or it will be auto-generated..."
        )
        self.transcript_edit.setMaximumHeight(200)
        transcript_layout.addWidget(self.transcript_edit)

        transcribe_btn = QPushButton("🎤 Auto-Transcribe")
        transcribe_btn.clicked.connect(self._auto_transcribe)
        transcript_layout.addWidget(transcribe_btn)

        layout.addWidget(transcript_group)

        # Transmute button
        self.transmute_btn = QPushButton("⚗️ TRANSMUTE")
        self.transmute_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFD700, stop:1 #FF8C00
                );
                color: black;
                border: none;
                border-radius: 8px;
                padding: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFA500, stop:1 #FF6B35
                );
            }
            QPushButton:disabled {
                background: #3a3a3a;
                color: #666666;
            }
        """)
        self.transmute_btn.clicked.connect(self._start_transmutation)
        layout.addWidget(self.transmute_btn)

        layout.addStretch()
        return panel

    def _create_output_panel(self) -> QWidget:
        """Create the output panel with asset tree."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(panel)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("✨ Generated Assets"))
        header.addStretch()

        self.build_btn = QPushButton("🔨 Build All")
        self.build_btn.clicked.connect(self._build_assets)
        self.build_btn.setEnabled(False)
        header.addWidget(self.build_btn)

        layout.addLayout(header)

        # Asset tree
        self.asset_tree = QTreeWidget()
        self.asset_tree.setHeaderLabels(["Asset", "Platform", "Status"])
        self.asset_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2a2a2a;
                border: none;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 8px;
            }
        """)
        layout.addWidget(self.asset_tree)

        # Insights
        insights_group = QGroupBox("💡 Core Insight")
        insights_layout = QVBoxLayout(insights_group)
        self.insight_label = QLabel("Transmute a video to see insights...")
        self.insight_label.setWordWrap(True)
        self.insight_label.setStyleSheet("color: #e0e0e0;")
        insights_layout.addWidget(self.insight_label)
        layout.addWidget(insights_group)

        return panel

    def _select_video(self) -> None:
        """Open file dialog to select video."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)",
        )
        if path:
            self._video_path = path
            self.video_label.setText(f"📹 {Path(path).name}")
            self.status_label.setText("Video selected. Add transcript and transmute!")

    def _auto_transcribe(self) -> None:
        """Auto-transcribe the video using Whisper."""
        if not self._video_path:
            show_toast(self, "Select a video first", "warning")
            return

        self.status_label.setText("🎤 Transcribing... (this may take a while)")

        try:
            from ...core.dynamic_captions import DynamicCaptions

            captions = DynamicCaptions()
            segments = captions.transcribe_with_words(self._video_path)

            # Build transcript text
            transcript = " ".join(seg.text for seg in segments)
            self.transcript_edit.setText(transcript)
            self.status_label.setText("✅ Transcription complete!")
            show_toast(self, "Transcription complete!", "success")

        except Exception as e:
            self.status_label.setText(f"❌ Transcription failed: {e}")
            show_toast(self, f"Transcription failed: {e}", "error")

    def _start_transmutation(self) -> None:
        """Start the transmutation process."""
        if not self._video_path:
            show_toast(self, "Select a video first", "warning")
            return

        transcript = self.transcript_edit.toPlainText().strip()
        if not transcript:
            show_toast(self, "Add a transcript first", "warning")
            return

        self._transcript = transcript
        self.transmute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("⚗️ Transmuting...")

        self._worker = TransmutationWorker(
            self._get_alchemist(), self._video_path, transcript
        )
        self._worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self._worker.finished.connect(self._on_transmutation_complete)
        self._worker.error.connect(self._on_transmutation_error)
        self._worker.start()

    def _on_transmutation_complete(self, result: TransmutationResult) -> None:
        """Handle completed transmutation."""
        self._current_result = result
        self.transmute_btn.setEnabled(True)
        self.build_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(
            f"✨ Transmutation complete! {len(result.assets)} assets generated"
        )

        # Update insight
        self.insight_label.setText(result.core_insight or "No insight extracted")

        # Populate tree
        self._populate_asset_tree(result)

        show_toast(self, f"Transmuted into {len(result.assets)} assets!", "success")

    def _on_transmutation_error(self, error: str) -> None:
        """Handle transmutation error."""
        self.transmute_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Transmutation failed: {error}")
        show_toast(self, f"Transmutation failed: {error}", "error")

    def _populate_asset_tree(self, result: TransmutationResult) -> None:
        """Populate the asset tree with results."""
        self.asset_tree.clear()

        platform_icons = {
            "linkedin": "💼",
            "twitter": "🐦",
            "tiktok": "🎵",
            "youtube_short": "📺",
            "instagram": "📷",
            "blog": "📝",
        }

        for asset in result.assets:
            icon = platform_icons.get(asset.platform, "📄")
            item = QTreeWidgetItem(
                [
                    f"{icon} {asset.title[:40]}",
                    asset.platform.title(),
                    "Ready to build",
                ]
            )
            self.asset_tree.addTopLevelItem(item)

    def _build_assets(self) -> None:
        """Build all generated assets."""
        if not self._current_result:
            return

        self.build_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)

        self._build_worker = AssetBuildWorker(self._get_factory(), self._current_result)
        self._build_worker.progress.connect(self._on_build_progress)
        self._build_worker.finished.connect(self._on_build_complete)
        self._build_worker.error.connect(self._on_build_error)
        self._build_worker.start()

    def _on_build_progress(self, message: str, percent: int) -> None:
        """Handle build progress."""
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_build_complete(self, assets: list) -> None:
        """Handle build completion."""
        self.build_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✅ Built {len(assets)} asset files!")

        # Update tree status
        for i in range(self.asset_tree.topLevelItemCount()):
            item = self.asset_tree.topLevelItem(i)
            if item:
                item.setText(2, "✅ Built")

        show_toast(self, f"Built {len(assets)} assets!", "success")

    def _on_build_error(self, error: str) -> None:
        """Handle build error."""
        self.build_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Build failed: {error}")
        show_toast(self, f"Build failed: {error}", "error")
