"""
Asset Browser: Media Library with semantic search.

Provides a visual interface for the AssetVault with:
- Grid/list view of all assets
- Semantic search via CLIP
- Filtering by type, tags, project
- Drag-and-drop support
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class AssetThumbnail(QFrame):
    """Display a single asset with thumbnail."""

    clicked = pyqtSignal(dict)
    double_clicked = pyqtSignal(dict)

    def __init__(self, asset_data: dict, parent=None):
        super().__init__(parent)
        self.asset_data = asset_data
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            AssetThumbnail {
                background: #1e2740;
                border-radius: 8px;
                border: 1px solid #2d3748;
            }
            AssetThumbnail:hover {
                border-color: #667eea;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(144, 100)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("""
            background: #0f111a;
            border-radius: 6px;
        """)
        self._load_thumbnail()
        layout.addWidget(self.thumb_label)

        # Filename
        filename = self.asset_data.get("filename", "Unknown")
        name_lbl = QLabel(filename[:18] + "..." if len(filename) > 18 else filename)
        name_lbl.setStyleSheet("color: white; font-size: 11px; font-weight: 500;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_lbl)

        # Type badge
        asset_type = self.asset_data.get("asset_type", "unknown")
        type_icons = {"image": "🖼️", "video": "🎬", "audio": "🎵", "document": "📄"}
        type_lbl = QLabel(f"{type_icons.get(asset_type, '📁')} {asset_type}")
        type_lbl.setStyleSheet("color: #8892a6; font-size: 10px;")
        type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(type_lbl)

    def _load_thumbnail(self):
        """Load thumbnail for asset."""
        filepath = self.asset_data.get("filepath", "")
        asset_type = self.asset_data.get("asset_type", "")

        if asset_type == "image" and Path(filepath).exists():
            pixmap = QPixmap(filepath)
            scaled = pixmap.scaled(
                144,
                100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(scaled)
        else:
            icons = {"image": "🖼️", "video": "🎬", "audio": "🎵", "document": "📄"}
            self.thumb_label.setText(icons.get(asset_type, "📁"))
            self.thumb_label.setStyleSheet("""
                background: #0f111a;
                border-radius: 6px;
                font-size: 32px;
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.asset_data)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.asset_data)


class AssetSearchThread(QThread):
    """Background thread for asset search."""

    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query: str, asset_type: str | None, limit: int = 50):
        super().__init__()
        self.query = query
        self.asset_type = asset_type
        self.limit = limit

    def run(self):
        try:
            from ...core.asset_vault import get_asset_vault

            vault = get_asset_vault()
            results = vault.search(
                query=self.query,
                asset_type=self.asset_type if self.asset_type else None,
                limit=self.limit,
            )
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class AssetBrowser(QWidget):
    """Main asset browser view."""

    asset_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assets: list[dict] = []
        self.thumbnails: list[AssetThumbnail] = []
        self._search_thread = None
        self._setup_ui()
        self._load_assets()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("📁 Asset Library")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")

        header.addWidget(title)
        header.addStretch()

        # Import button
        import_btn = QPushButton("📥 Import")
        import_btn.setStyleSheet("""
            QPushButton {
                background: #48bb78;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background: #38a169; }
        """)
        import_btn.clicked.connect(self._import_asset)
        header.addWidget(import_btn)

        layout.addLayout(header)

        # Search and filters
        filters = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search assets semantically...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 8px;
                padding: 12px 16px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #667eea; }
        """)
        self.search_input.returnPressed.connect(self._search)

        self.type_combo = QComboBox()
        self.type_combo.addItems(
            ["All Types", "Images", "Videos", "Audio", "Documents"]
        )
        self.type_combo.setStyleSheet("""
            QComboBox {
                background: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 8px;
                padding: 10px 16px;
                color: white;
                min-width: 120px;
            }
        """)
        self.type_combo.currentIndexChanged.connect(self._search)

        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a67d8; }
        """)
        search_btn.clicked.connect(self._search)

        filters.addWidget(self.search_input, 1)
        filters.addWidget(self.type_combo)
        filters.addWidget(search_btn)
        layout.addLayout(filters)

        # Stats bar
        self.stats_label = QLabel("Loading assets...")
        self.stats_label.setStyleSheet("color: #8892a6;")
        layout.addWidget(self.stats_label)

        # Asset grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll, 1)

    def _load_assets(self):
        """Load all assets from vault."""
        self._search()

    def _search(self):
        """Perform asset search."""
        query = self.search_input.text().strip()

        type_map = {
            0: None,  # All
            1: "image",
            2: "video",
            3: "audio",
            4: "document",
        }
        asset_type = type_map.get(self.type_combo.currentIndex())

        self.stats_label.setText("Searching...")

        self._search_thread = AssetSearchThread(query, asset_type)
        self._search_thread.results_ready.connect(self._display_results)
        self._search_thread.error.connect(self._on_error)
        self._search_thread.start()

    def _display_results(self, results: list):
        """Display search results."""
        self.assets = results

        # Clear existing thumbnails
        for thumb in self.thumbnails:
            thumb.deleteLater()
        self.thumbnails.clear()

        # Create thumbnail cards
        row, col = 0, 0
        max_cols = 6

        for asset in results:
            thumb = AssetThumbnail(asset)
            thumb.clicked.connect(self._on_asset_clicked)
            thumb.double_clicked.connect(self._on_asset_double_clicked)

            self.grid_layout.addWidget(thumb, row, col)
            self.thumbnails.append(thumb)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.stats_label.setText(f"Showing {len(results)} assets")

    def _on_error(self, message: str):
        """Handle search error."""
        self.stats_label.setText("Search failed")
        QMessageBox.warning(self, "Error", f"Asset search failed:\n{message}")

    def _on_asset_clicked(self, asset: dict):
        """Handle single click on asset."""
        self.asset_selected.emit(asset)

    def _on_asset_double_clicked(self, asset: dict):
        """Handle double click - open file."""
        import subprocess

        filepath = asset.get("filepath", "")
        if Path(filepath).exists():
            subprocess.run(["xdg-open", filepath], check=False)

    def _import_asset(self):
        """Import new asset to vault."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Asset",
            "",
            "Media Files (*.jpg *.jpeg *.png *.gif *.mp4 *.mov *.mp3 *.wav);;All Files (*)",
        )

        if filepath:
            try:
                from ...core.asset_vault import get_asset_vault

                vault = get_asset_vault()
                asset_id = vault.register(filepath, source="uploaded")
                if asset_id:
                    QMessageBox.information(
                        self, "Import", f"Asset imported successfully (ID: {asset_id})"
                    )
                    self._search()  # Refresh
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", str(e))
