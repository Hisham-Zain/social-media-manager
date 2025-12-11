"""
Brand Voice DNA Dashboard.

Visual interface for managing client personas and training AI on brand styles.
Leverages the existing StyleTuner backend for style analysis and adaptation.
"""

import json
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...ai.style_tuner import StyleProfile, StyleTuner
from ..widgets.style_metrics_widget import StyleMetricsWidget
from ..widgets.toasts import show_toast


class StyleAnalysisWorker(QThread):
    """Background worker for style analysis to prevent UI blocking."""

    finished = pyqtSignal(object)  # Emits StyleProfile or None
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        tuner: StyleTuner,
        client_id: str,
        samples: list[str],
        client_name: str,
    ) -> None:
        super().__init__()
        self.tuner = tuner
        self.client_id = client_id
        self.samples = samples
        self.client_name = client_name

    def run(self) -> None:
        try:
            self.progress.emit("Adding samples...")
            self.tuner.add_samples(
                self.client_id,
                self.samples,
                client_name=self.client_name,
            )

            self.progress.emit("Analyzing style...")
            profile = self.tuner.get_profile(self.client_id)
            self.finished.emit(profile)
        except Exception as e:
            logger.error(f"Style analysis failed: {e}")
            self.error.emit(str(e))


class TrainingWorker(QThread):
    """Background worker for adapter training."""

    finished = pyqtSignal(str)  # Emits adapter path
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, tuner: StyleTuner, client_id: str) -> None:
        super().__init__()
        self.tuner = tuner
        self.client_id = client_id

    def run(self) -> None:
        try:
            self.progress.emit("Training adapter (this may take a while)...")
            adapter_path = self.tuner.train_adapter(self.client_id)
            self.finished.emit(adapter_path or "")
        except Exception as e:
            logger.error(f"Adapter training failed: {e}")
            self.error.emit(str(e))


class DropZone(QFrame):
    """Drag-and-drop zone for sample files."""

    files_dropped = pyqtSignal(list)  # Emits list of file paths

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 2px dashed #555555;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #888888;
                background-color: #333333;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📁")
        icon.setFont(QFont("Segoe UI", 32))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text = QLabel("Drag & Drop Files Here")
        text.setFont(QFont("Segoe UI", 11))
        text.setStyleSheet("color: #aaaaaa;")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        subtext = QLabel("Supports: .txt, .md, .pdf, .json")
        subtext.setFont(QFont("Segoe UI", 9))
        subtext.setStyleSheet("color: #666666;")
        subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtext)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #3a3a5a;
                    border: 2px dashed #7777ff;
                    border-radius: 8px;
                }
            """)

    def dragLeaveEvent(self, event) -> None:
        self._setup_ui()

    def dropEvent(self, event: QDropEvent) -> None:
        self._setup_ui()
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).exists():
                files.append(path)
        if files:
            self.files_dropped.emit(files)


class BrandVoiceView(QWidget):
    """
    Brand Voice DNA Dashboard.

    Provides a visual interface for:
    - Managing client personas
    - Uploading writing samples
    - Viewing style metrics
    - Training style adapters
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_client: str | None = None
        self._samples: list[str] = []
        self._tuner: StyleTuner | None = None
        self._worker: StyleAnalysisWorker | None = None
        self._training_worker: TrainingWorker | None = None
        self._setup_ui()

    def _get_tuner(self) -> StyleTuner:
        """Lazy-load StyleTuner."""
        if self._tuner is None:
            self._tuner = StyleTuner()
        return self._tuner

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Client list
        left_panel = self._create_client_panel()
        splitter.addWidget(left_panel)

        # Center panel: Sample input & metrics
        center_panel = self._create_center_panel()
        splitter.addWidget(center_panel)

        # Right panel: Generation preview
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([200, 400, 300])
        layout.addWidget(splitter)

    def _create_client_panel(self) -> QWidget:
        """Create the client list panel."""
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #1e1e1e; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("🧬 Brand Voices")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Client list
        self.client_list = QListWidget()
        self.client_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a4a6a;
            }
            QListWidget::item:hover {
                background-color: #3a3a4a;
            }
        """)
        self.client_list.currentItemChanged.connect(self._on_client_selected)
        layout.addWidget(self.client_list)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add")
        add_btn.clicked.connect(self._add_client)
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self._delete_client)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        # Populate existing clients
        self._refresh_client_list()

        return panel

    def _create_center_panel(self) -> QWidget:
        """Create the sample input and metrics panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Selected client header
        self.selected_header = QLabel("Select a client to begin")
        self.selected_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(self.selected_header)

        # Drop zone for files
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._handle_dropped_files)
        layout.addWidget(self.drop_zone)

        # Or manual text input
        input_group = QGroupBox("📝 Or Paste Sample Text")
        input_layout = QVBoxLayout(input_group)

        self.sample_input = QPlainTextEdit()
        self.sample_input.setPlaceholderText(
            "Paste examples of the client's writing style here...\n\n"
            "Each paragraph will be treated as a separate sample."
        )
        self.sample_input.setMaximumHeight(100)
        input_layout.addWidget(self.sample_input)

        add_sample_btn = QPushButton("➕ Add as Sample")
        add_sample_btn.clicked.connect(self._add_text_sample)
        input_layout.addWidget(add_sample_btn)

        layout.addWidget(input_group)

        # Sample count indicator
        self.sample_indicator = QLabel("📊 0 samples loaded")
        self.sample_indicator.setStyleSheet("color: #888888;")
        layout.addWidget(self.sample_indicator)

        # Action buttons
        action_layout = QHBoxLayout()

        self.analyze_btn = QPushButton("🔍 Analyze Style")
        self.analyze_btn.clicked.connect(self._analyze_style)
        self.analyze_btn.setEnabled(False)
        action_layout.addWidget(self.analyze_btn)

        self.train_btn = QPushButton("🧠 Train Adapter")
        self.train_btn.clicked.connect(self._train_adapter)
        self.train_btn.setEnabled(False)
        action_layout.addWidget(self.train_btn)

        layout.addLayout(action_layout)

        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888888;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Style metrics display
        self.metrics_widget = StyleMetricsWidget()
        layout.addWidget(self.metrics_widget)

        return panel

    def _create_preview_panel(self) -> QWidget:
        """Create the generation preview panel."""
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #1e1e1e; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header = QLabel("✨ Preview Generation")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Prompt input
        prompt_group = QGroupBox("Generation Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Write a post about...")
        prompt_layout.addWidget(self.prompt_input)

        layout.addWidget(prompt_group)

        # Generate button
        self.generate_btn = QPushButton("🚀 Generate in Client Style")
        self.generate_btn.clicked.connect(self._generate_preview)
        self.generate_btn.setEnabled(False)
        layout.addWidget(self.generate_btn)

        # Output display
        output_group = QGroupBox("Generated Content")
        output_layout = QVBoxLayout(output_group)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setPlaceholderText("Generated content will appear here...")
        output_layout.addWidget(self.output_display)

        layout.addWidget(output_group)
        layout.addStretch()

        return panel

    def _refresh_client_list(self) -> None:
        """Populate the client list from StyleTuner."""
        self.client_list.clear()
        try:
            tuner = self._get_tuner()
            clients = tuner.list_clients()
            for client_id, profile in clients.items():
                item = QListWidgetItem(f"👤 {profile.name or client_id}")
                item.setData(Qt.ItemDataRole.UserRole, client_id)
                self.client_list.addItem(item)
        except Exception as e:
            logger.warning(f"Failed to load clients: {e}")

    def _on_client_selected(self, current: QListWidgetItem | None, _) -> None:
        """Handle client selection."""
        if current is None:
            self._current_client = None
            self.selected_header.setText("Select a client to begin")
            self.analyze_btn.setEnabled(False)
            self.train_btn.setEnabled(False)
            self.generate_btn.setEnabled(False)
            self.metrics_widget.clear_metrics()
            self._samples = []
            return

        self._current_client = current.data(Qt.ItemDataRole.UserRole)
        self.selected_header.setText(f"🧬 {current.text().replace('👤 ', '')}")

        # Load existing profile
        try:
            tuner = self._get_tuner()
            profile = tuner.get_profile(self._current_client)
            if profile:
                self._update_metrics_from_profile(profile)
                self.train_btn.setEnabled(True)
                self.generate_btn.setEnabled(True)
        except Exception as e:
            logger.warning(f"Failed to load profile: {e}")

    def _update_metrics_from_profile(self, profile: StyleProfile) -> None:
        """Update the metrics widget from a StyleProfile."""
        # Extract tone keywords from top phrases if available
        tone_keywords = getattr(profile, "top_phrases", [])[:5]
        if not tone_keywords:
            # Fallback: generate keywords based on metrics
            keywords = []
            if profile.emoji_frequency > 0.3:
                keywords.append("Emoji-heavy")
            if profile.formality_score < 0.3:
                keywords.append("Casual")
            elif profile.formality_score > 0.7:
                keywords.append("Formal")
            if profile.hashtag_frequency > 0.2:
                keywords.append("Hashtag-rich")
            if profile.vocabulary_richness > 0.7:
                keywords.append("Rich vocab")
            tone_keywords = keywords

        self.metrics_widget.update_metrics(
            emoji_freq=profile.emoji_frequency,
            hashtag_freq=profile.hashtag_frequency,
            vocab_richness=profile.vocabulary_richness,
            avg_sentence_len=profile.avg_sentence_length,
            formality=profile.formality_score,
            tone_keywords=tone_keywords,
            sample_count=profile.sample_count,
        )

    def _add_client(self) -> None:
        """Add a new client."""
        name, ok = QInputDialog.getText(self, "Add Client", "Enter client name:")
        if ok and name:
            # Create a simple ID from the name
            client_id = name.lower().replace(" ", "_")
            try:
                tuner = self._get_tuner()
                # Initialize with empty samples
                tuner.add_samples(client_id, [], client_name=name)
                self._refresh_client_list()
                show_toast(self, f"Added client: {name}", "success")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add client: {e}")

    def _delete_client(self) -> None:
        """Delete the selected client."""
        if not self._current_client:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete client '{self._current_client}' and all their data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                tuner = self._get_tuner()
                tuner.delete_client(self._current_client)
                self._refresh_client_list()
                self._current_client = None
                self.selected_header.setText("Select a client to begin")
                self.metrics_widget.clear_metrics()
                show_toast(self, "Client deleted", "success")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete: {e}")

    def _handle_dropped_files(self, files: list[str]) -> None:
        """Process dropped files."""
        if not self._current_client:
            show_toast(self, "Select a client first", "warning")
            return

        for file_path in files:
            path = Path(file_path)
            try:
                if path.suffix.lower() == ".pdf":
                    # Try to extract text from PDF
                    try:
                        import pypdf

                        reader = pypdf.PdfReader(str(path))
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        self._add_samples_from_text(text)
                    except ImportError:
                        show_toast(
                            self,
                            "Install pypdf for PDF support: pip install pypdf",
                            "warning",
                        )
                elif path.suffix.lower() == ".json":
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                        # Assume JSON is list of posts or has "content" field
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, str):
                                    self._samples.append(item)
                                elif isinstance(item, dict) and "content" in item:
                                    self._samples.append(item["content"])
                        elif isinstance(data, dict) and "posts" in data:
                            self._samples.extend(data["posts"])
                else:
                    # Plain text file
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                        self._add_samples_from_text(text)
            except Exception as e:
                logger.error(f"Failed to read file {path}: {e}")
                show_toast(self, f"Failed to read: {path.name}", "error")

        self._update_sample_count()

    def _add_samples_from_text(self, text: str) -> None:
        """Split text into samples and add to list."""
        # Split by double newlines or significant breaks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        self._samples.extend(paragraphs)

    def _add_text_sample(self) -> None:
        """Add manually entered text as samples."""
        if not self._current_client:
            show_toast(self, "Select a client first", "warning")
            return

        text = self.sample_input.toPlainText().strip()
        if text:
            self._add_samples_from_text(text)
            self.sample_input.clear()
            self._update_sample_count()
            show_toast(self, "Sample added", "success")

    def _update_sample_count(self) -> None:
        """Update the sample count indicator."""
        count = len(self._samples)
        self.sample_indicator.setText(f"📊 {count} samples loaded")
        self.analyze_btn.setEnabled(count > 0 and self._current_client is not None)

    def _analyze_style(self) -> None:
        """Run style analysis on collected samples."""
        if not self._current_client or not self._samples:
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.analyze_btn.setEnabled(False)

        # Get client name from list
        client_name = self._current_client
        for i in range(self.client_list.count()):
            item = self.client_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._current_client:
                client_name = item.text().replace("👤 ", "")
                break

        self._worker = StyleAnalysisWorker(
            self._get_tuner(),
            self._current_client,
            self._samples,
            client_name,
        )
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_analysis_progress(self, message: str) -> None:
        """Update progress label."""
        self.progress_label.setText(message)

    def _on_analysis_finished(self, profile: StyleProfile | None) -> None:
        """Handle analysis completion."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.analyze_btn.setEnabled(True)

        if profile:
            self._update_metrics_from_profile(profile)
            self.train_btn.setEnabled(True)
            self.generate_btn.setEnabled(True)
            show_toast(self, "Style analysis complete!", "success")
        else:
            show_toast(self, "Analysis returned no results", "warning")

    def _on_analysis_error(self, error: str) -> None:
        """Handle analysis error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.analyze_btn.setEnabled(True)
        show_toast(self, f"Analysis failed: {error}", "error")

    def _train_adapter(self) -> None:
        """Train a LoRA adapter for the current client."""
        if not self._current_client:
            return

        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.train_btn.setEnabled(False)

        self._training_worker = TrainingWorker(self._get_tuner(), self._current_client)
        self._training_worker.progress.connect(self._on_analysis_progress)
        self._training_worker.finished.connect(self._on_training_finished)
        self._training_worker.error.connect(self._on_training_error)
        self._training_worker.start()

    def _on_training_finished(self, adapter_path: str) -> None:
        """Handle training completion."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.train_btn.setEnabled(True)

        if adapter_path:
            show_toast(self, f"Adapter trained: {adapter_path}", "success")
        else:
            show_toast(
                self,
                "Using prompt-based styling (Unsloth not available)",
                "info",
            )

    def _on_training_error(self, error: str) -> None:
        """Handle training error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.train_btn.setEnabled(True)
        show_toast(self, f"Training failed: {error}", "error")

    def _generate_preview(self) -> None:
        """Generate content in client's style."""
        if not self._current_client:
            return

        prompt = self.prompt_input.text().strip()
        if not prompt:
            show_toast(self, "Enter a generation prompt", "warning")
            return

        self.generate_btn.setEnabled(False)
        self.output_display.setPlaceholderText("Generating...")

        try:
            tuner = self._get_tuner()
            result = tuner.generate_styled(self._current_client, prompt)
            self.output_display.setPlainText(result or "No output generated")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            self.output_display.setPlainText(f"Error: {e}")
        finally:
            self.generate_btn.setEnabled(True)
