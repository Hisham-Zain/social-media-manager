"""
Job Queue View for tracking background tasks.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...job_queue import JobStatus, get_queue


class JobQueueView(QWidget):
    """View to monitor and manage background jobs."""

    def __init__(self):
        super().__init__()
        self.queue = get_queue()
        self._setup_ui()

        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_jobs)
        self.timer.start(1000)  # Every second

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📋 Job Queue")
        title.setObjectName("h1")

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_jobs)

        clear_btn = QPushButton("🧹 Clear Completed")
        clear_btn.clicked.connect(self._clear_completed)

        clear_failed_btn = QPushButton("🗑️ Clean Failed")
        clear_failed_btn.clicked.connect(self._clear_failed)
        clear_failed_btn.setStyleSheet("background-color: #ff4444; color: white;")

        retry_all_btn = QPushButton("🔁 Retry All Failed")
        retry_all_btn.clicked.connect(self._retry_all_failed)
        retry_all_btn.setStyleSheet("background-color: #FFBB33; color: black;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        header_layout.addWidget(clear_btn)
        header_layout.addWidget(clear_failed_btn)
        header_layout.addWidget(retry_all_btn)
        layout.addLayout(header_layout)

        # Stats row
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet(
            "color: #a0aec0; font-size: 13px; margin: 8px 0;"
        )
        layout.addWidget(self.stats_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Job ID", "Type", "Status", "Progress", "Created At", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(5, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 8px;
                gridline-color: #0f3460;
            }
            QHeaderView::section {
                background-color: #0f3460;
                color: white;
                padding: 8px;
                border: none;
            }
        """)
        layout.addWidget(self.table)

    def _refresh_jobs(self):
        jobs = self.queue.get_jobs(limit=50)
        self.table.setRowCount(len(jobs))

        # Calculate stats
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        pending = sum(
            1 for j in jobs if j.status in (JobStatus.PENDING, JobStatus.QUEUED)
        )
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)

        self.stats_label.setText(
            f"📊 Total: {len(jobs)} | "
            f"🔄 Running: {running} | "
            f"⏳ Pending: {pending} | "
            f"✅ Completed: {completed} | "
            f"❌ Failed: {failed}"
        )

        for row, job in enumerate(jobs):
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(job.id[:8]))

            # Type
            self.table.setItem(row, 1, QTableWidgetItem(job.job_type))

            # Status (Colored)
            status_item = QTableWidgetItem(job.status.value.upper())
            color = "#4F8BF9"  # Blue default
            if job.status == JobStatus.COMPLETED:
                color = "#00C851"
            elif job.status == JobStatus.FAILED:
                color = "#ff4444"
            elif job.status == JobStatus.RUNNING:
                color = "#FFBB33"
            elif job.status == JobStatus.CANCELLED:
                color = "#666666"

            status_item.setForeground(QColor("#ffffff"))
            status_item.setBackground(QColor(color))
            self.table.setItem(row, 2, status_item)

            # Progress Bar
            pbar = QProgressBar()
            pbar.setValue(int(job.progress))
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #0f3460;
                    border-radius: 4px;
                    text-align: center;
                    color: white;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                }}
            """)
            self.table.setCellWidget(row, 3, pbar)

            # Created At
            self.table.setItem(row, 4, QTableWidgetItem(job.created_at[:19]))

            # Actions - buttons for retry/cancel
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            if job.status == JobStatus.FAILED:
                retry_btn = QPushButton("🔁")
                retry_btn.setToolTip("Retry this job")
                retry_btn.setFixedSize(30, 26)
                retry_btn.setStyleSheet("background: #FFBB33; border-radius: 4px;")
                retry_btn.clicked.connect(lambda _, jid=job.id: self._retry_job(jid))
                actions_layout.addWidget(retry_btn)

                delete_btn = QPushButton("🗑️")
                delete_btn.setToolTip("Delete this job")
                delete_btn.setFixedSize(30, 26)
                delete_btn.setStyleSheet("background: #ff4444; border-radius: 4px;")
                delete_btn.clicked.connect(lambda _, jid=job.id: self._delete_job(jid))
                actions_layout.addWidget(delete_btn)

            elif job.status in (JobStatus.PENDING, JobStatus.QUEUED):
                cancel_btn = QPushButton("❌")
                cancel_btn.setToolTip("Cancel this job")
                cancel_btn.setFixedSize(30, 26)
                cancel_btn.setStyleSheet("background: #ff4444; border-radius: 4px;")
                cancel_btn.clicked.connect(lambda _, jid=job.id: self._cancel_job(jid))
                actions_layout.addWidget(cancel_btn)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 5, actions_widget)

    def _retry_job(self, job_id: str):
        if self.queue.retry_job(job_id):
            self._refresh_jobs()

    def _cancel_job(self, job_id: str):
        if self.queue.cancel_job(job_id):
            self._refresh_jobs()

    def _delete_job(self, job_id: str):
        """Delete a specific job from the database."""
        self.queue.delete_job(job_id)
        self._refresh_jobs()

    def _clear_completed(self):
        self.queue.clear_completed(older_than_hours=0)
        self._refresh_jobs()

    def _clear_failed(self):
        """Remove all failed jobs from the queue."""
        self.queue.clear_failed()
        self._refresh_jobs()

    def _retry_all_failed(self):
        """Retry all failed jobs."""
        jobs = self.queue.get_jobs(status=JobStatus.FAILED, limit=100)
        count = 0
        for job in jobs:
            if self.queue.retry_job(job.id):
                count += 1
        if count > 0:
            QMessageBox.information(self, "Retry", f"Retried {count} failed jobs.")
        else:
            QMessageBox.information(self, "Retry", "No failed jobs to retry.")
        self._refresh_jobs()
