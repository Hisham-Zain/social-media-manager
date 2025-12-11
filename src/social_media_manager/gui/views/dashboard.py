"""
Dashboard view for the desktop GUI.

Premium dashboard with:
- Gradient stat cards with icons
- Real-time system metrics
- Activity feed with timestamps
- Quick actions panel
- Kanban project board
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

try:
    from ..widgets.system_monitor import SystemMonitorWidget
except ImportError:
    SystemMonitorWidget = None

try:
    from ..widgets.kanban import KanbanBoard
except ImportError:
    KanbanBoard = None


class StatCard(QFrame):
    """Premium gradient stat card."""

    def __init__(
        self, title: str, value: str, icon: str, color: str = "#818cf8"
    ) -> None:
        super().__init__()
        self._color = color
        self.setStyleSheet("""
            StatCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 41, 59, 0.8), stop:1 rgba(15, 23, 42, 0.9));
                border-radius: 16px;
                border: 1px solid rgba(51, 65, 85, 0.5);
            }
        """)
        self.setMinimumSize(180, 130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Icon with glow effect
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {color}33, stop:1 transparent);
            border-radius: 12px;
            padding: 8px;
        """)
        layout.addWidget(icon_label)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 800;
            color: {color};
            letter-spacing: -1px;
        """)
        layout.addWidget(self.value_label)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #64748b;
            font-size: 13px;
            font-weight: 600;
        """)
        layout.addWidget(title_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class QuickActionButton(QPushButton):
    """Stylish quick action button."""

    def __init__(self, icon: str, label: str, color: str = "#818cf8"):
        super().__init__(f"{icon}  {label}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}20, stop:1 transparent);
                border: 1px solid {color}40;
                border-radius: 12px;
                padding: 14px 20px;
                color: {color};
                font-weight: 600;
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}35, stop:1 {color}10);
                border-color: {color};
            }}
        """)


class ActivityItem(QFrame):
    """Single activity item with timestamp."""

    def __init__(self, icon: str, text: str, time: str = "Just now"):
        super().__init__()
        self.setStyleSheet("""
            ActivityItem {
                background: transparent;
                border-bottom: 1px solid rgba(51, 65, 85, 0.3);
                padding: 4px 0;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px; min-width: 28px;")
        layout.addWidget(icon_lbl)

        # Text
        text_lbl = QLabel(text)
        text_lbl.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        layout.addWidget(text_lbl, 1)

        # Time
        time_lbl = QLabel(time)
        time_lbl.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(time_lbl)


class DashboardView(QWidget):
    """Premium dashboard with stats, actions, activity feed, and Kanban."""

    # Signal to request navigation to another view
    navigate_to_view = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._start_refresh_timer()

    def _navigate_to(self, index: int) -> None:
        """Emit navigation signal to switch views."""
        self.navigate_to_view.emit(index)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # === HEADER ===
        header = QHBoxLayout()

        title_section = QVBoxLayout()
        title_section.setSpacing(4)

        title = QLabel("📊 Dashboard")
        title.setObjectName("h1")
        title_section.addWidget(title)

        subtitle = QLabel("Welcome back! Here's what's happening.")
        subtitle.setObjectName("subtitle")
        title_section.addWidget(subtitle)

        header.addLayout(title_section)
        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄  Refresh")
        refresh_btn.setObjectName("ghost")
        refresh_btn.clicked.connect(self._refresh_stats)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # === STAT CARDS ROW ===
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.jobs_card = StatCard("Active Jobs", "0", "⚙️", "#818cf8")
        self.videos_card = StatCard("Videos Today", "0", "🎬", "#34d399")
        self.gpu_card = StatCard("GPU Usage", "N/A", "🔥", "#f59e0b")
        self.queue_card = StatCard("Queue Size", "0", "📋", "#f472b6")

        stats_row.addWidget(self.jobs_card)
        stats_row.addWidget(self.videos_card)
        stats_row.addWidget(self.gpu_card)
        stats_row.addWidget(self.queue_card)

        layout.addLayout(stats_row)

        # === MAIN CONTENT SPLITTER ===
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # === TOP ROW: System Monitor + Quick Actions ===
        top_widget = QWidget()
        content_row = QHBoxLayout(top_widget)
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(24)

        # System Monitor
        if SystemMonitorWidget:
            monitor_container = QFrame()
            monitor_container.setObjectName("card")
            monitor_container.setStyleSheet("""
                QFrame#card {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(30, 41, 59, 0.6), stop:1 rgba(15, 23, 42, 0.8));
                    border: 1px solid rgba(51, 65, 85, 0.4);
                    border-radius: 20px;
                }
            """)
            monitor_layout = QVBoxLayout(monitor_container)
            monitor_label = QLabel("🖥️ System Monitor")
            monitor_label.setStyleSheet(
                "font-size: 15px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px;"
            )
            monitor_layout.addWidget(monitor_label)
            self.monitor = SystemMonitorWidget()
            monitor_layout.addWidget(self.monitor)
            content_row.addWidget(monitor_container, 2)
        else:
            placeholder = QLabel("System Monitor Not Available")
            placeholder.setStyleSheet("color: #64748b; padding: 40px;")
            content_row.addWidget(placeholder, 2)

        # Quick Actions
        actions_container = QFrame()
        actions_container.setObjectName("card")
        actions_container.setStyleSheet("""
            QFrame#card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 41, 59, 0.6), stop:1 rgba(15, 23, 42, 0.8));
                border: 1px solid rgba(51, 65, 85, 0.4);
                border-radius: 20px;
            }
        """)
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setSpacing(12)

        actions_label = QLabel("⚡ Quick Actions")
        actions_label.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px;"
        )
        actions_layout.addWidget(actions_label)

        # Actions with their target view indices
        actions = [
            ("🎬", "New Video Project", "#818cf8", 1),  # Content Studio
            ("📤", "Upload Content", "#34d399", 2),  # Media Library
            ("🤖", "AI Generate", "#f59e0b", 5),  # AI Tools
            ("📊", "View Analytics", "#f472b6", 6),  # Job Queue
        ]

        self.action_buttons = []
        for icon, label, color, target_idx in actions:
            btn = QuickActionButton(icon, label, color)
            btn.clicked.connect(lambda _, idx=target_idx: self._navigate_to(idx))
            actions_layout.addWidget(btn)
            self.action_buttons.append(btn)

        actions_layout.addStretch()
        content_row.addWidget(actions_container, 1)

        main_splitter.addWidget(top_widget)

        # === BOTTOM ROW: Kanban Board ===
        if KanbanBoard:
            kanban_container = QFrame()
            kanban_container.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(30, 41, 59, 0.6), stop:1 rgba(15, 23, 42, 0.8));
                    border: 1px solid rgba(51, 65, 85, 0.4);
                    border-radius: 20px;
                }
            """)
            kanban_layout = QVBoxLayout(kanban_container)
            kanban_layout.setContentsMargins(16, 16, 16, 16)

            self.kanban = KanbanBoard()
            self.kanban.add_demo_projects()  # Add demo data
            kanban_layout.addWidget(self.kanban)

            main_splitter.addWidget(kanban_container)
        else:
            # Fallback: Activity Feed
            activity_container = QFrame()
            activity_container.setObjectName("card")
            activity_container.setStyleSheet("""
                QFrame#card {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(30, 41, 59, 0.6), stop:1 rgba(15, 23, 42, 0.8));
                    border: 1px solid rgba(51, 65, 85, 0.4);
                    border-radius: 20px;
                }
            """)
            activity_layout = QVBoxLayout(activity_container)

            activity_header = QHBoxLayout()
            activity_label = QLabel("📝 Recent Activity")
            activity_label.setStyleSheet(
                "font-size: 15px; font-weight: 700; color: #e2e8f0;"
            )
            activity_header.addWidget(activity_label)
            activity_header.addStretch()
            view_all = QLabel("View All →")
            view_all.setStyleSheet("color: #818cf8; font-size: 12px; font-weight: 600;")
            activity_header.addWidget(view_all)
            activity_layout.addLayout(activity_header)

            activities = [
                ("🎬", "Video generated: product_demo.mp4", "2 min ago"),
                ("📤", "Uploaded to Instagram @brand", "15 min ago"),
                ("✏️", "Caption generated for campaign", "1 hour ago"),
                ("🔍", "Trend analysis completed", "2 hours ago"),
                ("✨", "AI upscaled 3 images to 4K", "3 hours ago"),
            ]
            for icon, text, time in activities:
                activity_layout.addWidget(ActivityItem(icon, text, time))

            main_splitter.addWidget(activity_container)

        main_splitter.setSizes([300, 400])
        layout.addWidget(main_splitter, 1)

    def _start_refresh_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_stats)
        self.timer.start(3000)
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                self.gpu_card.set_value(f"{result.stdout.strip()}%")
        except Exception:
            self.gpu_card.set_value("N/A")

        # Update job count from queue
        try:
            from ...job_queue import _instance

            if _instance:
                active = sum(
                    1
                    for j in _instance._jobs.values()
                    if j.status.value in ["pending", "running"]
                )
                self.jobs_card.set_value(str(active))
                self.queue_card.set_value(str(len(_instance._jobs)))
        except Exception:
            pass
