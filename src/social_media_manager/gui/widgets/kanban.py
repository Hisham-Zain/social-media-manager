"""
Kanban Board for AgencyOS.

Client-centric project tracking with drag-and-drop between columns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QMouseEvent,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    pass


class KanbanCard(QFrame):
    """A draggable card representing a project."""

    clicked: pyqtSignal = pyqtSignal(str)  # project_id
    moved: pyqtSignal = pyqtSignal(str, str)  # project_id, new_column

    def __init__(
        self,
        project_id: str,
        title: str,
        client: str = "",
        platform: str = "",
        job_id: str = "",
    ) -> None:
        super().__init__()
        self.project_id: str = project_id
        self.title: str = title
        self.client: str = client
        self.platform: str = platform
        self.job_id: str = job_id  # Link to job queue
        self._drag_start_pos: QPoint | None = None

        self._setup_ui()
        self.setAcceptDrops(False)

    def _setup_ui(self) -> None:
        self.setFixedHeight(100)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet("""
            KanbanCard {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
            }
            KanbanCard:hover {
                border-color: #8b5cf6;
                background: #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Platform icon + title
        title_row = QHBoxLayout()
        platform_icons: dict[str, str] = {
            "tiktok": "📱",
            "youtube": "▶️",
            "instagram": "📷",
            "linkedin": "💼",
        }
        icon = platform_icons.get(self.platform.lower(), "🎬")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        title_row.addWidget(icon_label)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #e2e8f0;
            background: transparent;
        """)
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)
        layout.addLayout(title_row)

        # Client name
        if self.client:
            client_label = QLabel(f"👤 {self.client}")
            client_label.setStyleSheet("""
                font-size: 11px;
                color: #94a3b8;
                background: transparent;
            """)
            layout.addWidget(client_label)

        layout.addStretch()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event and self._drag_start_pos:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance >= 10:  # Start drag after minimum distance
                self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if event:
            self.clicked.emit(self.project_id)
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        """Start drag operation."""
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.project_id)
        drag.setMimeData(mime)

        # Create pixmap of card for drag preview
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio))
        drag.setHotSpot(self.rect().center())

        drag.exec(Qt.DropAction.MoveAction)


class KanbanColumn(QFrame):
    """A column in the Kanban board that accepts dropped cards."""

    card_dropped: pyqtSignal = pyqtSignal(str, str)  # project_id, column_id

    def __init__(self, column_id: str, title: str, color: str = "#8b5cf6") -> None:
        super().__init__()
        self.column_id: str = column_id
        self.color: str = color
        self.cards: dict[str, KanbanCard] = {}
        self.count_label: QLabel
        self.card_container: QWidget
        self.card_layout: QVBoxLayout

        self._setup_ui(title)
        self.setAcceptDrops(True)

    def _setup_ui(self, title: str) -> None:
        self.setMinimumWidth(220)
        self.setStyleSheet("""
            KanbanColumn {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        # Color dot + title
        dot = QLabel("●")
        dot.setStyleSheet(
            f"color: {self.color}; font-size: 12px; background: transparent;"
        )
        header_layout.addWidget(dot)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #e2e8f0;
            background: transparent;
        """)
        header_layout.addWidget(title_label)

        # Count badge
        self.count_label = QLabel("0")
        self.count_label.setFixedSize(24, 24)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("""
            background: #334155;
            color: #94a3b8;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.count_label)

        layout.addWidget(header)

        # Scrollable card area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self.card_container = QWidget()
        self.card_container.setStyleSheet("background: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(8)
        self.card_layout.addStretch()

        scroll.setWidget(self.card_container)
        layout.addWidget(scroll, 1)

    def add_card(self, card: KanbanCard) -> None:
        """Add a card to this column."""
        self.cards[card.project_id] = card
        # Insert before the stretch
        self.card_layout.insertWidget(self.card_layout.count() - 1, card)
        self._update_count()

    def remove_card(self, project_id: str) -> KanbanCard | None:
        """Remove and return a card from this column."""
        if project_id in self.cards:
            card = self.cards.pop(project_id)
            self.card_layout.removeWidget(card)
            self._update_count()
            return card
        return None

    def _update_count(self) -> None:
        self.count_label.setText(str(len(self.cards)))

    def dragEnterEvent(self, event: "QDragEnterEvent | None") -> None:
        if event and event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet("""
                KanbanColumn {
                    background: #1e293b;
                    border: 2px dashed #8b5cf6;
                    border-radius: 12px;
                }
            """)

    def dragLeaveEvent(self, event: "QDragLeaveEvent | None") -> None:
        self.setStyleSheet("""
            KanbanColumn {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)

    def dropEvent(self, event: "QDropEvent | None") -> None:
        if event and event.mimeData().hasText():
            project_id = event.mimeData().text()
            self.card_dropped.emit(project_id, self.column_id)
            event.acceptProposedAction()
        self.setStyleSheet("""
            KanbanColumn {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)


class KanbanBoard(QWidget):
    """Complete Kanban board with drag-drop between columns."""

    card_moved: pyqtSignal = pyqtSignal(str, str, str)  # project_id, from, to

    COLUMNS: list[tuple[str, str, str]] = [
        ("idea", "💡 Idea", "#f59e0b"),
        ("scripting", "✍️ Scripting", "#3b82f6"),
        ("rendering", "🎬 Rendering", "#8b5cf6"),
        ("review", "👀 Review", "#ec4899"),
        ("published", "✅ Published", "#22c55e"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.columns: dict[str, KanbanColumn] = {}
        self._project_columns: dict[
            str, str
        ] = {}  # Track which column each project is in
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("📋 Project Board")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e2e8f0;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Columns container with horizontal scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        columns_widget = QWidget()
        columns_layout = QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(12)

        for col_id, col_title, color in self.COLUMNS:
            column = KanbanColumn(col_id, col_title, color)
            column.card_dropped.connect(self._on_card_dropped)
            self.columns[col_id] = column
            columns_layout.addWidget(column)

        scroll.setWidget(columns_widget)
        layout.addWidget(scroll, 1)

    def _on_card_dropped(self, project_id: str, to_column: str) -> None:
        """Handle card dropped on a column."""
        from_column = self._project_columns.get(project_id)
        if from_column and from_column != to_column:
            self.move_project(project_id, from_column, to_column)

    def add_project(
        self,
        project_id: str,
        title: str,
        column: str = "idea",
        client: str = "",
        platform: str = "",
        job_id: str = "",
    ) -> None:
        """Add a project card to the board."""
        if column not in self.columns:
            column = "idea"

        card = KanbanCard(project_id, title, client, platform, job_id)
        self.columns[column].add_card(card)
        self._project_columns[project_id] = column

    def move_project(self, project_id: str, from_column: str, to_column: str) -> bool:
        """Move a project between columns."""
        if from_column not in self.columns or to_column not in self.columns:
            return False

        card = self.columns[from_column].remove_card(project_id)
        if card:
            self.columns[to_column].add_card(card)
            self._project_columns[project_id] = to_column
            self.card_moved.emit(project_id, from_column, to_column)
            return True
        return False

    def get_project_column(self, project_id: str) -> str | None:
        """Get the current column of a project."""
        return self._project_columns.get(project_id)

    def on_job_status_changed(self, job_id: str, status: str) -> None:
        """Update card position based on job status."""
        # Find the card with this job_id
        for col_id, column in self.columns.items():
            for card in column.cards.values():
                if card.job_id == job_id:
                    # Map job status to Kanban column
                    status_to_column = {
                        "pending": "scripting",
                        "running": "rendering",
                        "completed": "review",
                        "failed": "idea",  # Move back for retry
                    }
                    new_column = status_to_column.get(status)
                    if new_column and new_column != col_id:
                        self.move_project(card.project_id, col_id, new_column)
                    return

    def add_demo_projects(self) -> None:
        """Add demo projects for testing."""
        self.add_project("p1", "TikTok Viral Hook", "idea", "Nike", "tiktok")
        self.add_project(
            "p2", "Product Launch Reel", "scripting", "Adidas", "instagram"
        )
        self.add_project("p3", "Tutorial Video", "rendering", "Apple", "youtube")
        self.add_project("p4", "Company Update", "review", "Tesla", "linkedin")
        self.add_project("p5", "Holiday Campaign", "published", "Coca-Cola", "tiktok")
