"""
Toast Notifications for AgencyOS GUI.

Non-blocking notifications that slide in from the corner.
"""

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class ToastNotification(QWidget):
    """A toast notification that slides in and auto-dismisses."""

    COLORS = {
        "success": "#22c55e",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6",
    }

    def __init__(
        self,
        parent: QWidget,
        message: str,
        toast_type: str = "success",
        duration_ms: int = 3000,
    ):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self._setup_ui(message, toast_type)
        self._setup_animation()

    def _setup_ui(self, message: str, toast_type: str) -> None:
        self.setFixedWidth(320)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        color = self.COLORS.get(toast_type, self.COLORS["info"])

        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: #1e293b;
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)

        # Icon based on type
        icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
        icon_label = QLabel(icons.get(toast_type, "ℹ️"))
        icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            background: transparent;
        """)
        layout.addWidget(msg_label, 1)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #e2e8f0;
            }
        """)
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)

        self.adjustSize()

    def _setup_animation(self) -> None:
        # Start off-screen
        parent = self.parent()
        if parent:
            start_x = parent.width()
            end_x = parent.width() - self.width() - 20
            y_pos = parent.height() - self.height() - 20

            self.move(start_x, y_pos)

            # Slide-in animation
            self.slide_in = QPropertyAnimation(self, b"pos")
            self.slide_in.setDuration(300)
            self.slide_in.setStartValue(QPoint(start_x, y_pos))
            self.slide_in.setEndValue(QPoint(end_x, y_pos))
            self.slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_toast(self) -> None:
        """Show the toast with animation."""
        self.show()
        self.raise_()
        self.slide_in.start()

        # Auto-dismiss after duration
        QTimer.singleShot(self.duration_ms, self._dismiss)

    def _dismiss(self) -> None:
        """Fade out and close."""
        self.close()
        self.deleteLater()


class ToastManager:
    """Manages toast notifications for a parent widget."""

    _active_toasts: list[ToastNotification] = []

    @classmethod
    def show_toast(
        cls,
        parent: QWidget,
        message: str,
        toast_type: str = "success",
        duration_ms: int = 3000,
    ) -> None:
        """Show a toast notification."""
        toast = ToastNotification(parent, message, toast_type, duration_ms)

        # Stack toasts vertically
        offset = len(cls._active_toasts) * 80
        if parent:
            toast.move(
                parent.width() - toast.width() - 20,
                parent.height() - toast.height() - 20 - offset,
            )

        cls._active_toasts.append(toast)
        toast.show_toast()

        # Remove from list when closed
        def on_close() -> None:
            if toast in cls._active_toasts:
                cls._active_toasts.remove(toast)

        toast.destroyed.connect(on_close)


def show_toast(
    parent: QWidget,
    message: str,
    toast_type: str = "success",
    duration_ms: int = 3000,
) -> None:
    """Convenience function to show a toast."""
    ToastManager.show_toast(parent, message, toast_type, duration_ms)
