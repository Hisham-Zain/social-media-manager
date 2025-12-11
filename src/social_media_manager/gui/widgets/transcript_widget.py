"""
Transcript Editor Widget for Text-Based Video Editing.

Displays transcript with word-level selection for editing.
Words can be marked for deletion and the video is re-cut accordingly.

Features:
- Selectable word display with highlighting
- Keep/Delete toggle with Color coding
- Keyboard shortcuts (D=delete, K=keep, Ctrl+Z=undo)
- Edit statistics display
"""

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut, QTextCharFormat
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.transcript_editor import TranscriptDocument, TranscriptEditor
from ..widgets.toasts import show_toast


class TranscriptionWorker(QThread):
    """Background worker for video transcription."""

    finished = pyqtSignal(object)  # Emits TranscriptDocument
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, editor: TranscriptEditor, video_path: str) -> None:
        super().__init__()
        self.editor = editor
        self.video_path = video_path

    def run(self) -> None:
        try:
            self.progress.emit("Transcribing video (this may take a while)...")
            doc = self.editor.transcribe(self.video_path)
            self.finished.emit(doc)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Background worker for video export."""

    finished = pyqtSignal(str)  # Emits output path
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self, editor: TranscriptEditor, output_path: str | None = None
    ) -> None:
        super().__init__()
        self.editor = editor
        self.output_path = output_path

    def run(self) -> None:
        try:
            self.progress.emit("Applying transcript edits to video...")
            result = self.editor.export_edited_video(self.output_path)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.error.emit(str(e))


class TranscriptEditorWidget(QWidget):
    """
    Widget for text-based video editing.

    Displays transcript with word selection. Users can mark words
    for deletion and the video will be automatically re-cut.

    Signals:
        video_exported: Emitted when video export completes (path)
    """

    video_exported = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = TranscriptEditor()
        self._document: TranscriptDocument | None = None
        self._video_path: str = ""
        self._selection_start: int = 0
        self._selection_end: int = 0
        self._transcription_worker: TranscriptionWorker | None = None
        self._export_worker: ExportWorker | None = None
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header with load button
        header = QHBoxLayout()

        title = QLabel("✂️ Text-Based Video Editor")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.addWidget(title)

        header.addStretch()

        self.load_btn = QPushButton("📁 Load Video")
        self.load_btn.clicked.connect(self._load_video)
        self.load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a5a7a;
            }
        """)
        header.addWidget(self.load_btn)

        layout.addLayout(header)

        # Instructions
        instructions = QLabel(
            "Select text and press <b>D</b> to delete, <b>K</b> to keep. "
            "Use <b>Ctrl+Z</b> to undo."
        )
        instructions.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(instructions)

        # Progress indicator
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888888;")
        progress_layout.addWidget(self.progress_label)

        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)

        # Transcript display
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setReadOnly(False)  # Allow selection
        self.transcript_edit.setFont(QFont("Segoe UI", 12))
        self.transcript_edit.setPlaceholderText(
            "Load a video file to see its transcript here.\n\n"
            "The transcript will appear with word-level timing.\n"
            "Select words and press D to delete them from the video."
        )
        self.transcript_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 16px;
                color: #e0e0e0;
                line-height: 1.8;
            }
        """)
        self.transcript_edit.selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.transcript_edit, 1)

        # Stats bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)

        self.words_label = QLabel("Words: 0")
        self.words_label.setStyleSheet("color: #ffffff;")
        stats_layout.addWidget(self.words_label)

        self.deleted_label = QLabel("Deleted: 0")
        self.deleted_label.setStyleSheet("color: #F44336;")
        stats_layout.addWidget(self.deleted_label)

        self.time_label = QLabel("Time saved: 0s")
        self.time_label.setStyleSheet("color: #4CAF50;")
        stats_layout.addWidget(self.time_label)

        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # Action buttons
        actions = QHBoxLayout()

        self.undo_btn = QPushButton("↩️ Undo")
        self.undo_btn.clicked.connect(self._undo)
        self.undo_btn.setEnabled(False)
        actions.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↪️ Redo")
        self.redo_btn.clicked.connect(self._redo)
        self.redo_btn.setEnabled(False)
        actions.addWidget(self.redo_btn)

        actions.addStretch()

        self.preview_btn = QPushButton("👁️ Preview Cuts")
        self.preview_btn.clicked.connect(self._preview_cuts)
        self.preview_btn.setEnabled(False)
        actions.addWidget(self.preview_btn)

        self.export_btn = QPushButton("💾 Export Video")
        self.export_btn.clicked.connect(self._export_video)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)
        actions.addWidget(self.export_btn)

        layout.addLayout(actions)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # D - Delete selected
        delete_shortcut = QShortcut(QKeySequence("D"), self)
        delete_shortcut.activated.connect(self._delete_selection)

        # K - Keep selected
        keep_shortcut = QShortcut(QKeySequence("K"), self)
        keep_shortcut.activated.connect(self._keep_selection)

        # Ctrl+Z - Undo
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._undo)

        # Ctrl+Shift+Z - Redo
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.activated.connect(self._redo)

    def _load_video(self) -> None:
        """Open file dialog to load a video."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)",
        )
        if path:
            self._video_path = path
            self._start_transcription()

    def _start_transcription(self) -> None:
        """Begin transcription in background."""
        self.progress_container.setVisible(True)
        self.progress_label.setText("Initializing transcription...")
        self.load_btn.setEnabled(False)

        self._transcription_worker = TranscriptionWorker(self._editor, self._video_path)
        self._transcription_worker.progress.connect(self._on_progress)
        self._transcription_worker.finished.connect(self._on_transcription_complete)
        self._transcription_worker.error.connect(self._on_transcription_error)
        self._transcription_worker.start()

    def _on_progress(self, message: str) -> None:
        """Update progress display."""
        self.progress_label.setText(message)

    def _on_transcription_complete(self, doc: TranscriptDocument) -> None:
        """Handle completed transcription."""
        self.progress_container.setVisible(False)
        self.load_btn.setEnabled(True)
        self._document = doc
        self._display_transcript()
        self._update_stats()
        self.export_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        show_toast(self, f"Transcription complete! {len(doc.words)} words.", "success")

    def _on_transcription_error(self, error: str) -> None:
        """Handle transcription error."""
        self.progress_container.setVisible(False)
        self.load_btn.setEnabled(True)
        show_toast(self, f"Transcription failed: {error}", "error")

    def _display_transcript(self) -> None:
        """Display the transcript with color coding."""
        if not self._document:
            return

        self.transcript_edit.clear()
        cursor = self.transcript_edit.textCursor()

        for word in self._document.words:
            # Set format based on state
            fmt = QTextCharFormat()
            if word.state == "delete":
                fmt.setForeground(QColor("#F44336"))
                fmt.setFontStrikeOut(True)
                fmt.setBackground(QColor("#3a2a2a"))
            elif word.state == "keep":
                fmt.setForeground(QColor("#4CAF50"))
                fmt.setBackground(QColor("#2a3a2a"))
            else:
                fmt.setForeground(QColor("#e0e0e0"))

            cursor.insertText(word.word + " ", fmt)

        self.transcript_edit.setTextCursor(cursor)

    def _on_selection_changed(self) -> None:
        """Track selection for word-level operations."""
        cursor = self.transcript_edit.textCursor()
        if cursor.hasSelection():
            self._selection_start = cursor.selectionStart()
            self._selection_end = cursor.selectionEnd()

    def _get_selected_word_indices(self) -> list[int]:
        """Get indices of words in the current selection."""
        if not self._document:
            return []

        # Calculate character positions for each word
        pos = 0
        indices = []
        for word in self._document.words:
            word_end = pos + len(word.word) + 1  # +1 for space
            if pos < self._selection_end and word_end > self._selection_start:
                indices.append(word.index)
            pos = word_end

        return indices

    def _delete_selection(self) -> None:
        """Mark selected words for deletion."""
        indices = self._get_selected_word_indices()
        if indices:
            self._editor.mark_for_deletion(indices)
            self._display_transcript()
            self._update_stats()
            self.undo_btn.setEnabled(True)

    def _keep_selection(self) -> None:
        """Mark selected words to keep."""
        indices = self._get_selected_word_indices()
        if indices:
            self._editor.mark_for_keep(indices)
            self._display_transcript()
            self._update_stats()
            self.undo_btn.setEnabled(True)

    def _undo(self) -> None:
        """Undo last edit."""
        if self._editor.undo():
            self._display_transcript()
            self._update_stats()
            self.redo_btn.setEnabled(True)

    def _redo(self) -> None:
        """Redo last undone edit."""
        if self._editor.redo():
            self._display_transcript()
            self._update_stats()

    def _update_stats(self) -> None:
        """Update statistics display."""
        stats = self._editor.get_edit_stats()
        if stats:
            self.words_label.setText(f"Words: {stats['total_words']}")
            self.deleted_label.setText(
                f"Deleted: {stats['deleted_words']} ({stats['deleted_percent']:.0f}%)"
            )
            self.time_label.setText(f"Time saved: {stats['time_removed']:.1f}s")

    def _preview_cuts(self) -> None:
        """Show preview of what will be cut."""
        cuts = self._editor.generate_cut_list()
        if cuts:
            msg = f"Video will contain {len(cuts)} segments:\n\n"
            for i, (start, end) in enumerate(cuts[:10], 1):
                msg += f"  {i}. {start:.1f}s - {end:.1f}s ({end - start:.1f}s)\n"
            if len(cuts) > 10:
                msg += f"\n  ... and {len(cuts) - 10} more segments"

            QMessageBox.information(self, "Preview Cuts", msg)
        else:
            show_toast(self, "No segments to keep!", "warning")

    def _export_video(self) -> None:
        """Export the edited video."""
        if not self._document:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Edited Video",
            "",
            "MP4 Video (*.mp4);;All Files (*)",
        )
        if path:
            self.progress_container.setVisible(True)
            self.progress_label.setText("Exporting edited video...")
            self.export_btn.setEnabled(False)

            self._export_worker = ExportWorker(self._editor, path)
            self._export_worker.progress.connect(self._on_progress)
            self._export_worker.finished.connect(self._on_export_complete)
            self._export_worker.error.connect(self._on_export_error)
            self._export_worker.start()

    def _on_export_complete(self, path: str) -> None:
        """Handle export completion."""
        self.progress_container.setVisible(False)
        self.export_btn.setEnabled(True)
        show_toast(self, f"Video exported: {path}", "success")
        self.video_exported.emit(path)

    def _on_export_error(self, error: str) -> None:
        """Handle export error."""
        self.progress_container.setVisible(False)
        self.export_btn.setEnabled(True)
        show_toast(self, f"Export failed: {error}", "error")

    def load_video(self, path: str) -> None:
        """Load a video file programmatically."""
        self._video_path = path
        self._start_transcription()
