"""
Sidebar navigation for the desktop GUI.

Premium sidebar with:
- Gradient background
- Smooth hover animations
- Active state indicators
- Brand identity header
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    """Premium sidebar navigation widget."""

    navigation_changed = pyqtSignal(int)

    NAV_ITEMS = [
        ("📊", "Dashboard", 0),
        ("🎬", "Content Studio", 1),
        ("🎨", "Storyboard", 2),
        ("📁", "Asset Library", 3),
        ("📚", "Media Library", 4),
        ("⚡", "Automation", 5),
        ("🎯", "Strategy Room", 6),
        ("🤖", "AI Tools", 7),
        ("📋", "Job Queue", 8),
        ("💬", "Community", 9),
        ("🧬", "Brand Voice", 10),
        ("🎭", "War Room", 11),
        ("⚗️", "Alchemy", 12),
        ("⚙️", "Settings", 13),
    ]

    def __init__(self) -> None:
        """Initialize the sidebar."""
        super().__init__()
        self.setFixedWidth(240)
        self.setStyleSheet("""
            Sidebar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.5 #0a0e17, stop:1 #05070f);
                border-right: 1px solid rgba(30, 41, 59, 0.8);
            }
        """)

        self._current_index = 0
        self._buttons: list[QPushButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === BRAND HEADER ===
        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(99, 102, 241, 0.15), stop:1 transparent);
                border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        brand = QLabel("🚀 AgencyOS")
        brand.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: white;
            background: transparent;
            letter-spacing: -0.5px;
        """)

        tagline = QLabel("AI-Powered Content")
        tagline.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #818cf8;
            background: transparent;
            letter-spacing: 1px;
            text-transform: uppercase;
        """)

        header_layout.addWidget(brand)
        header_layout.addWidget(tagline)
        layout.addWidget(header)

        # === NAV SECTION LABEL ===
        nav_label = QLabel("  NAVIGATION")
        nav_label.setStyleSheet("""
            color: #475569;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 20px 20px 10px 20px;
            background: transparent;
        """)
        layout.addWidget(nav_label)

        # === NAVIGATION BUTTONS ===
        for icon, label, index in self.NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self._on_nav_click(i))
            btn.setStyleSheet(self._get_button_style(index == 0))
            self._buttons.append(btn)
            layout.addWidget(btn)

        # === SPACER ===
        layout.addStretch()

        # === BOTTOM SECTION ===
        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 16, 16, 16)
        bottom_layout.setSpacing(8)

        # Pro badge
        pro_badge = QLabel("✨ Pro Edition")
        pro_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pro_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(99, 102, 241, 0.2), stop:1 rgba(168, 85, 247, 0.2));
            border: 1px solid rgba(129, 140, 248, 0.3);
            border-radius: 8px;
            padding: 8px 16px;
            color: #c7d2fe;
            font-size: 13px;
            font-weight: 600;
        """)
        bottom_layout.addWidget(pro_badge)

        version = QLabel("v3.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("""
            color: #334155;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)
        bottom_layout.addWidget(version)

        layout.addWidget(bottom)

    def _get_button_style(self, active: bool) -> str:
        """Get button stylesheet based on active state."""
        if active:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(99, 102, 241, 0.25), stop:1 transparent);
                    color: #c7d2fe;
                    border: none;
                    border-left: 3px solid #818cf8;
                    text-align: left;
                    padding-left: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    border-radius: 0;
                }
            """
        return """
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                border-left: 3px solid transparent;
                text-align: left;
                padding-left: 20px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(99, 102, 241, 0.1), stop:1 transparent);
                color: #e2e8f0;
                border-left: 3px solid rgba(129, 140, 248, 0.5);
            }
        """

    def _on_nav_click(self, index: int) -> None:
        """Handle navigation button click."""
        if index == self._current_index:
            return

        # Update button styles
        self._buttons[self._current_index].setStyleSheet(self._get_button_style(False))
        self._buttons[index].setStyleSheet(self._get_button_style(True))

        self._current_index = index
        self.navigation_changed.emit(index)
