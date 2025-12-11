"""
Media Library View for the Desktop GUI.

Visual search and footage indexing using VisualRAG.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class IndexWorker(QThread):
    """Background worker for indexing media."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(int)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        try:
            from ...ai.visual_rag import VisualRAG

            rag = VisualRAG()
            folder = Path(self.folder_path)
            videos = list(folder.glob("*.mp4")) + list(folder.glob("*.mkv"))

            total = len(videos)
            for i, video in enumerate(videos):
                self.progress.emit(int((i / max(total, 1)) * 100), video.name)
                rag.index_video(str(video))

            self.finished.emit(total)
        except Exception as e:
            self.progress.emit(0, f"Error: {e}")
            self.finished.emit(0)


class MediaLibraryView(QWidget):
    """Media Library with visual search and indexing."""

    def __init__(self):
        super().__init__()
        self._rag = None
        self._setup_ui()

    def _get_rag(self):
        if not self._rag:
            try:
                from ...ai.visual_rag import VisualRAG

                self._rag = VisualRAG()
            except Exception:
                pass
        return self._rag

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("📚 Media Library")
        title.setObjectName("h1")
        subtitle = QLabel("Visual search and footage indexing")
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
        tabs.addTab(self._create_search_tab(), "🔍 Visual Search")
        tabs.addTab(self._create_index_tab(), "📂 Index Footage")
        tabs.addTab(self._create_browse_tab(), "📁 Browse")
        layout.addWidget(tabs, 1)

    def _create_search_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search input
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Describe what you're looking for... (e.g., 'sunset beach scene')"
        )
        search_btn = QPushButton("🔍 Search")
        search_btn.setObjectName("primary")
        search_btn.clicked.connect(self._do_search)

        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #2d3748;
            }
            QListWidget::item:selected {
                background: rgba(102, 126, 234, 0.3);
            }
        """)
        results_layout.addWidget(self.results_list)

        layout.addWidget(results_group, 1)
        return widget

    def _create_index_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Folder selection
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder containing videos...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_folder)

        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Index button
        self.index_btn = QPushButton("🚀 Start Indexing")
        self.index_btn.setObjectName("primary")
        self.index_btn.clicked.connect(self._start_indexing)
        layout.addWidget(self.index_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.addStretch()
        return widget

    def _create_browse_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Browse indexed footage and manage your library.")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        self.indexed_list = QListWidget()
        self.indexed_list.setStyleSheet("""
            QListWidget { background: #1a202c; border-radius: 8px; }
            QListWidget::item { padding: 10px; }
        """)
        layout.addWidget(self.indexed_list, 1)

        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self._refresh_indexed)
        layout.addWidget(refresh_btn)

        return widget

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        rag = self._get_rag()
        if not rag:
            self.results_list.addItem("Visual RAG not available")
            return

        try:
            matches = rag.search(query, top_k=10)
            for match in matches:
                item = QListWidgetItem(
                    f"📹 {match.video_path} @ {match.timestamp:.1f}s (Score: {match.score:.2f})"
                )
                self.results_list.addItem(item)

            if not matches:
                self.results_list.addItem("No matches found")
        except Exception as e:
            self.results_list.addItem(f"Error: {e}")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder:
            self.folder_input.setText(folder)

    def _start_indexing(self):
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Error", "Please select a folder first")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.index_btn.setEnabled(False)

        self.worker = IndexWorker(folder)
        self.worker.progress.connect(self._on_index_progress)
        self.worker.finished.connect(self._on_index_done)
        self.worker.start()

    def _on_index_progress(self, percent: int, status: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Indexing: {status}")

    def _on_index_done(self, count: int):
        self.progress_bar.setVisible(False)
        self.index_btn.setEnabled(True)
        self.status_label.setText(f"✅ Indexed {count} videos")
        QMessageBox.information(self, "Done", f"Successfully indexed {count} videos!")

    def _refresh_indexed(self):
        self.indexed_list.clear()
        rag = self._get_rag()
        if rag:
            try:
                stats = rag.get_stats()
                self.indexed_list.addItem(
                    f"Total videos: {stats.get('total_videos', 0)}"
                )
                self.indexed_list.addItem(
                    f"Total frames: {stats.get('total_frames', 0)}"
                )
            except Exception:
                self.indexed_list.addItem("Could not load statistics")
