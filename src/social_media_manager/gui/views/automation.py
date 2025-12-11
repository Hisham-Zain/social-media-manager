"""
Automation Hub View for the Desktop GUI.

Batch processing and watch folder automation.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...job_queue import JobPriority, submit_job


class AutomationView(QWidget):
    """Automation Hub for batch processing."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("⚡ Automation Hub")
        title.setObjectName("h1")
        subtitle = QLabel("Batch processing and automated workflows")
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
        tabs.addTab(self._create_batch_tab(), "📦 Batch Process")
        tabs.addTab(self._create_watch_tab(), "👁️ Watch Folder")
        tabs.addTab(self._create_templates_tab(), "📋 Templates")
        layout.addWidget(tabs, 1)

    def _create_batch_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # File selection
        files_group = QGroupBox("Select Files")
        files_layout = QVBoxLayout(files_group)

        select_row = QHBoxLayout()
        self.batch_folder = QLineEdit()
        self.batch_folder.setPlaceholderText("Select folder or drag files...")
        browse_btn = QPushButton("Browse Folder")
        browse_btn.clicked.connect(self._browse_batch_folder)
        select_row.addWidget(self.batch_folder, 1)
        select_row.addWidget(browse_btn)
        files_layout.addLayout(select_row)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        files_layout.addWidget(self.file_list)

        layout.addWidget(files_group)

        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(
            [
                "Generate Captions",
                "Transcribe",
                "Upscale",
                "Remove Background",
                "Create Thumbnails",
                "Full Video Process",
            ]
        )
        row1.addWidget(self.action_combo, 1)
        options_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Platform:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(
            ["YouTube", "TikTok/Shorts", "Instagram", "All Platforms"]
        )
        row2.addWidget(self.platform_combo, 1)
        options_layout.addLayout(row2)

        layout.addWidget(options_group)

        # Progress
        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        layout.addWidget(self.batch_progress)

        self.batch_status = QLabel("")
        layout.addWidget(self.batch_status)

        # Start button
        self.start_btn = QPushButton("🚀 Start Batch Processing")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_batch)
        layout.addWidget(self.start_btn)

        layout.addStretch()
        return widget

    def _create_watch_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Watch folder config
        folder_group = QGroupBox("Watch Folder Configuration")
        folder_layout = QVBoxLayout(folder_group)

        row = QHBoxLayout()
        self.watch_folder = QLineEdit()
        self.watch_folder.setPlaceholderText("~/Videos/incoming")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_watch_folder)
        row.addWidget(self.watch_folder, 1)
        row.addWidget(browse_btn)
        folder_layout.addLayout(row)

        # Auto-process options
        auto_row = QHBoxLayout()
        auto_row.addWidget(QLabel("Auto-process as:"))
        self.auto_action = QComboBox()
        self.auto_action.addItems(
            ["Full Video", "Transcribe Only", "Caption + Thumbnail"]
        )
        auto_row.addWidget(self.auto_action, 1)
        folder_layout.addLayout(auto_row)

        layout.addWidget(folder_group)

        # Control buttons
        btn_row = QHBoxLayout()
        self.watch_btn = QPushButton("▶️ Start Watching")
        self.watch_btn.setObjectName("success")
        self.watch_btn.clicked.connect(self._toggle_watch)
        btn_row.addWidget(self.watch_btn)

        self.watch_status = QLabel("Status: Stopped")
        btn_row.addWidget(self.watch_status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        self.watch_log = QListWidget()
        log_layout.addWidget(self.watch_log)
        layout.addWidget(log_group, 1)

        return widget

    def _create_goals_tab(self) -> QWidget:
        """Create the Goal Setting tab for autonomy engine."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Description
        info = QLabel(
            "Set goals for the Autonomy Engine. "
            "It will automatically adjust content strategy to meet targets."
        )
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Goal list
        goals_group = QGroupBox("Active Goals")
        goals_layout = QVBoxLayout(goals_group)

        self.goals_list = QListWidget()
        self.goals_list.addItem("📈 Engagement: 0 / 5,000 (0%)")
        self.goals_list.addItem("👁️ Views: 0 / 10,000 (0%)")
        self.goals_list.addItem("📝 Posts: 0 / 7 this week (0%)")
        goals_layout.addWidget(self.goals_list)

        # Add goal form
        form_row = QHBoxLayout()
        form_row.addWidget(QLabel("Metric:"))
        self.goal_metric = QComboBox()
        self.goal_metric.addItems(["Engagement", "Views", "Followers", "Posts"])
        form_row.addWidget(self.goal_metric)

        form_row.addWidget(QLabel("Target:"))
        self.goal_target = QLineEdit()
        self.goal_target.setPlaceholderText("e.g., 5000")
        self.goal_target.setFixedWidth(100)
        form_row.addWidget(self.goal_target)

        add_goal_btn = QPushButton("➕ Add Goal")
        add_goal_btn.clicked.connect(self._add_goal)
        form_row.addWidget(add_goal_btn)
        form_row.addStretch()
        goals_layout.addLayout(form_row)

        layout.addWidget(goals_group)

        # Niche settings
        niche_group = QGroupBox("Content Strategy")
        niche_layout = QVBoxLayout(niche_group)

        niche_row = QHBoxLayout()
        niche_row.addWidget(QLabel("Target Niche:"))
        self.niche_input = QLineEdit()
        self.niche_input.setText("Tech")
        self.niche_input.setPlaceholderText("e.g., Tech, Finance, Lifestyle")
        niche_row.addWidget(self.niche_input, 1)
        niche_layout.addLayout(niche_row)

        layout.addWidget(niche_group)

        # Run controls
        btn_row = QHBoxLayout()
        self.run_cycle_btn = QPushButton("🔄 Run Daily Cycle")
        self.run_cycle_btn.setObjectName("primary")
        self.run_cycle_btn.clicked.connect(self._run_autonomy_cycle)
        btn_row.addWidget(self.run_cycle_btn)

        self.autonomy_status = QLabel("Status: Idle")
        btn_row.addWidget(self.autonomy_status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Results display
        results_group = QGroupBox("Last Cycle Results")
        results_layout = QVBoxLayout(results_group)
        self.cycle_results = QListWidget()
        self.cycle_results.setMaximumHeight(120)
        results_layout.addWidget(self.cycle_results)
        layout.addWidget(results_group)

        layout.addStretch()
        return widget

    def _create_templates_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Create reusable processing templates for common workflows.")
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Template list
        self.template_list = QListWidget()
        self.template_list.addItem("📹 YouTube Long-form → Shorts + Clips")
        self.template_list.addItem("🎙️ Podcast → Audiogram + Transcript")
        self.template_list.addItem("📸 Product Shoot → Social Posts")
        self.template_list.addItem("📰 Blog → Video + Carousel")
        layout.addWidget(self.template_list, 1)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("➕ New Template")
        new_btn.clicked.connect(self._new_template)
        edit_btn = QPushButton("✏️ Edit")
        run_btn = QPushButton("▶️ Run Template")
        run_btn.setObjectName("primary")

        btn_row.addWidget(new_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addStretch()
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)

        return widget

    def _browse_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.batch_folder.setText(folder)
            self._scan_folder(folder)

    def _scan_folder(self, folder: str):
        self.file_list.clear()
        path = Path(folder)
        extensions = [".mp4", ".mkv", ".mov", ".jpg", ".png", ".mp3", ".wav"]
        for f in path.iterdir():
            if f.suffix.lower() in extensions:
                self.file_list.addItem(f.name)

    def _start_batch(self):
        folder = self.batch_folder.text().strip()
        if not folder:
            QMessageBox.warning(self, "Error", "Please select a folder first")
            return

        action = self.action_combo.currentText()
        platform = self.platform_combo.currentText()

        # Submit batch job
        payload = {
            "folder": folder,
            "action": action,
            "platform": platform,
        }

        job_id = submit_job("batch_process", payload, JobPriority.NORMAL)
        self.batch_status.setText(f"✅ Batch job started: {job_id[:8]}...")
        QMessageBox.information(
            self,
            "Batch Started",
            f"Batch processing job submitted!\n\nJob ID: {job_id[:12]}...\n\n"
            "Check the Job Queue for progress.",
        )

    def _browse_watch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Watch Folder")
        if folder:
            self.watch_folder.setText(folder)

    def _toggle_watch(self):
        if self.watch_btn.text().startswith("▶️"):
            self.watch_btn.setText("⏹️ Stop Watching")
            self.watch_status.setText("Status: Watching...")
            self.watch_status.setStyleSheet("color: #48bb78;")
            self.watch_log.addItem(f"Started watching: {self.watch_folder.text()}")
        else:
            self.watch_btn.setText("▶️ Start Watching")
            self.watch_status.setText("Status: Stopped")
            self.watch_status.setStyleSheet("")
            self.watch_log.addItem("Stopped watching")

    def _new_template(self):
        QMessageBox.information(
            self,
            "Coming Soon",
            "Template editor coming soon!\n\nFor now, use the existing templates.",
        )

    def _add_goal(self) -> None:
        """Add a new goal to the autonomy engine."""
        metric = self.goal_metric.currentText()
        target_text = self.goal_target.text().strip()

        if not target_text:
            QMessageBox.warning(self, "Error", "Please enter a target value")
            return

        try:
            target = int(target_text.replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "Error", "Target must be a number")
            return

        # Add to UI list
        emoji = {"Engagement": "📈", "Views": "👁️", "Followers": "👥", "Posts": "📝"}
        self.goals_list.addItem(
            f"{emoji.get(metric, '🎯')} {metric}: 0 / {target:,} (0%)"
        )

        # Clear input
        self.goal_target.clear()

        QMessageBox.information(
            self,
            "Goal Added",
            f"Added goal: {metric} → {target:,}\n\n"
            "The Autonomy Engine will track this goal.",
        )

    def _run_autonomy_cycle(self) -> None:
        """Submit an autonomy cycle job."""
        niche = self.niche_input.text().strip() or "Tech"

        # Submit the job
        payload = {"niche": niche}
        job_id = submit_job("autonomy_cycle", payload, JobPriority.NORMAL)

        self.autonomy_status.setText("Status: Running...")
        self.autonomy_status.setStyleSheet("color: #f6ad55;")
        self.cycle_results.clear()
        self.cycle_results.addItem(f"✨ Cycle started: {job_id[:8]}...")
        self.cycle_results.addItem(f"📊 Analyzing trends for: {niche}")
        self.cycle_results.addItem("⏳ Check Job Queue for progress")

        QMessageBox.information(
            self,
            "Autonomy Cycle Started",
            f"Daily cycle job submitted!\n\n"
            f"Niche: {niche}\nJob ID: {job_id[:12]}...\n\n"
            "Monitor the Job Queue for results.",
        )
