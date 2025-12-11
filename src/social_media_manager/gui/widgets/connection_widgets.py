"""
Connection UI Widgets for the Settings View.

Provides visual components for displaying and managing platform connections:
- ConnectionCard: Main card widget for each platform
- TokenStatusBadge: Color-coded health indicator
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.connections import PlatformConnection


class TokenStatusBadge(QLabel):
    """
    Color-coded badge showing token health status.

    States:
    - 🟢 Green: Valid (>7 days until expiry)
    - 🟡 Yellow: Expiring Soon (<7 days)
    - 🔴 Red: Expired
    - ⚪ Gray: Not Connected
    """

    STATUS_STYLES = {
        "valid": {
            "bg": "#059669",
            "text": "Connected",
            "icon": "✓",
        },
        "expiring": {
            "bg": "#d97706",
            "text": "Expiring Soon",
            "icon": "⚠",
        },
        "expired": {
            "bg": "#dc2626",
            "text": "Expired",
            "icon": "✕",
        },
        "disconnected": {
            "bg": "#475569",
            "text": "Not Connected",
            "icon": "○",
        },
    }

    def __init__(self, status: str = "disconnected", parent: QWidget | None = None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        """Update the badge to show the given status."""
        style = self.STATUS_STYLES.get(status, self.STATUS_STYLES["disconnected"])

        self.setText(f" {style['icon']} {style['text']} ")
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {style["bg"]};
                color: white;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )


class ConnectionCard(QFrame):
    """
    Visual card widget for a social media platform connection.

    Displays:
    - Platform icon and name
    - Connection status badge
    - Account name (if connected)
    - Token expiry info
    - Scopes/permissions
    - Connect/Disconnect/Refresh buttons
    """

    # Signals for button actions
    connect_clicked = pyqtSignal(str)  # platform
    disconnect_clicked = pyqtSignal(str)  # platform
    refresh_clicked = pyqtSignal(str)  # platform

    def __init__(self, connection: PlatformConnection, parent: QWidget | None = None):
        super().__init__(parent)
        self.connection = connection
        self.platform = connection.platform
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the card UI."""
        self.setObjectName("connectionCard")
        self.setStyleSheet(
            """
            QFrame#connectionCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 41, 59, 0.8), stop:1 rgba(15, 23, 42, 0.9));
                border: 1px solid rgba(51, 65, 85, 0.5);
                border-radius: 12px;
                padding: 16px;
                margin: 4px 0;
            }
            QFrame#connectionCard:hover {
                border-color: rgba(99, 102, 241, 0.5);
            }
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Left: Platform icon and info
        left_section = QVBoxLayout()
        left_section.setSpacing(4)

        # Platform header (icon + name)
        header = QHBoxLayout()
        header.setSpacing(10)

        info = self.connection.info
        icon_label = QLabel(info.get("icon", "🔗"))
        icon_label.setStyleSheet("font-size: 28px;")
        header.addWidget(icon_label)

        name_label = QLabel(info.get("name", self.platform.title()))
        name_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #f1f5f9;")
        header.addWidget(name_label)
        header.addStretch()

        left_section.addLayout(header)

        # Account info (if connected)
        self.account_label = QLabel()
        self.account_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        left_section.addWidget(self.account_label)

        # Expiry info
        self.expiry_label = QLabel()
        self.expiry_label.setStyleSheet("color: #64748b; font-size: 12px;")
        left_section.addWidget(self.expiry_label)

        layout.addLayout(left_section, 1)

        # Middle: Status badge
        middle_section = QVBoxLayout()
        middle_section.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_badge = TokenStatusBadge()
        middle_section.addWidget(self.status_badge)

        # Scopes/permissions
        self.scopes_label = QLabel()
        self.scopes_label.setStyleSheet(
            "color: #64748b; font-size: 11px; font-style: italic;"
        )
        self.scopes_label.setWordWrap(True)
        self.scopes_label.setMaximumWidth(200)
        middle_section.addWidget(self.scopes_label)

        layout.addLayout(middle_section)

        # Right: Action buttons
        right_section = QVBoxLayout()
        right_section.setSpacing(8)
        right_section.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                padding: 8px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #818cf8, stop:1 #a78bfa);
            }
            """
        )
        self.connect_btn.clicked.connect(
            lambda: self.connect_clicked.emit(self.platform)
        )
        right_section.addWidget(self.connect_btn)

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #475569;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                border-color: #818cf8;
                color: #c7d2fe;
            }
            """
        )
        self.refresh_btn.clicked.connect(
            lambda: self.refresh_clicked.emit(self.platform)
        )
        right_section.addWidget(self.refresh_btn)

        # Disconnect button
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #dc2626;
                border-radius: 8px;
                color: #f87171;
                padding: 8px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: rgba(220, 38, 38, 0.2);
            }
            """
        )
        self.disconnect_btn.clicked.connect(
            lambda: self.disconnect_clicked.emit(self.platform)
        )
        right_section.addWidget(self.disconnect_btn)

        layout.addLayout(right_section)

        # Update UI with current connection state
        self.update_connection(self.connection)

    def update_connection(self, connection: PlatformConnection) -> None:
        """Update the card UI with new connection data."""
        self.connection = connection

        # Update status badge
        self.status_badge.set_status(connection.health_status)

        # Update account info
        if connection.connected and connection.account_name:
            self.account_label.setText(f"Account: {connection.account_name}")
            self.account_label.show()
        else:
            self.account_label.hide()

        # Update expiry info
        if connection.connected:
            days = connection.days_until_expiry
            if days is not None:
                if days == 0:
                    self.expiry_label.setText("Token expired!")
                    self.expiry_label.setStyleSheet(
                        "color: #f87171; font-size: 12px; font-weight: 600;"
                    )
                elif days == 1:
                    self.expiry_label.setText("Expires tomorrow")
                    self.expiry_label.setStyleSheet("color: #fbbf24; font-size: 12px;")
                elif days <= 7:
                    self.expiry_label.setText(f"Expires in {days} days")
                    self.expiry_label.setStyleSheet("color: #fbbf24; font-size: 12px;")
                else:
                    self.expiry_label.setText(f"Valid for {days} days")
                    self.expiry_label.setStyleSheet("color: #64748b; font-size: 12px;")
                self.expiry_label.show()
            else:
                self.expiry_label.setText("No expiration")
                self.expiry_label.show()
        else:
            self.expiry_label.hide()

        # Update scopes
        if connection.connected and connection.scopes:
            scope_text = ", ".join(
                s.split("/")[-1] if "/" in s else s for s in connection.scopes[:3]
            )
            if len(connection.scopes) > 3:
                scope_text += f" +{len(connection.scopes) - 3} more"
            self.scopes_label.setText(f"Scopes: {scope_text}")
            self.scopes_label.show()
        else:
            self.scopes_label.hide()

        # Update button visibility
        if connection.connected:
            self.connect_btn.hide()
            self.refresh_btn.show()
            self.disconnect_btn.show()
        else:
            self.connect_btn.show()
            self.refresh_btn.hide()
            self.disconnect_btn.hide()
