"""
Storyboard View: Visual pre-visualization for video production.

Allows users to:
- Generate storyboard from script
- Preview static images for each scene
- Regenerate individual scenes
- Swap with stock footage
- Approve scenes before rendering
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SceneCard(QFrame):
    """Display a single scene with preview and controls."""

    regenerate_requested = pyqtSignal(int)
    swap_stock_requested = pyqtSignal(int)
    approve_toggled = pyqtSignal(int, bool)

    def __init__(self, scene_data: dict, parent=None):
        super().__init__(parent)
        self.scene_data = scene_data
        self.scene_id = scene_data.get("id", 0)
        self._approved = scene_data.get("status") == "approved"
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            SceneCard {
                background: #1e2740;
                border-radius: 12px;
                border: 1px solid #2d3748;
            }
            SceneCard:hover {
                border-color: #667eea;
            }
        """)
        self.setMinimumSize(280, 320)
        self.setMaximumSize(320, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Scene number badge
        header = QHBoxLayout()
        scene_num = QLabel(f"Scene {self.scene_id + 1}")
        scene_num.setStyleSheet("""
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 11px;
        """)

        duration = self.scene_data.get("duration", 0)
        duration_lbl = QLabel(f"{duration:.1f}s")
        duration_lbl.setStyleSheet("color: #8892a6; font-size: 11px;")

        header.addWidget(scene_num)
        header.addStretch()
        header.addWidget(duration_lbl)
        layout.addLayout(header)

        # Preview image
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(256, 144)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            background: #0f111a;
            border: 1px solid #2d3748;
            border-radius: 8px;
        """)
        self._load_preview()
        layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Script segment
        script_segment = self.scene_data.get("script_segment", "")
        script_lbl = QLabel(
            script_segment[:80] + "..." if len(script_segment) > 80 else script_segment
        )
        script_lbl.setWordWrap(True)
        script_lbl.setStyleSheet("color: #a0aec0; font-size: 11px;")
        script_lbl.setMaximumHeight(40)
        layout.addWidget(script_lbl)

        # Status indicator
        status = self.scene_data.get("status", "pending")
        status_colors = {
            "pending": "#718096",
            "generating": "#ecc94b",
            "generated": "#48bb78",
            "approved": "#667eea",
            "failed": "#e53e3e",
        }
        status_lbl = QLabel(f"● {status.capitalize()}")
        status_lbl.setStyleSheet(
            f"color: {status_colors.get(status, '#718096')}; font-size: 11px;"
        )
        layout.addWidget(status_lbl)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.approve_btn = QPushButton("✓" if self._approved else "Approve")
        self.approve_btn.setCheckable(True)
        self.approve_btn.setChecked(self._approved)
        self.approve_btn.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background: #4a5568; }
            QPushButton:checked { background: #48bb78; }
        """)
        self.approve_btn.clicked.connect(self._on_approve)

        regen_btn = QPushButton("🔄")
        regen_btn.setToolTip("Regenerate")
        regen_btn.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        regen_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.scene_id))

        stock_btn = QPushButton("📸")
        stock_btn.setToolTip("Swap with stock")
        stock_btn.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        stock_btn.clicked.connect(lambda: self.swap_stock_requested.emit(self.scene_id))

        actions.addWidget(self.approve_btn)
        actions.addStretch()
        actions.addWidget(regen_btn)
        actions.addWidget(stock_btn)
        layout.addLayout(actions)

    def _load_preview(self):
        """Load preview image from scene data."""
        image_path = self.scene_data.get("image_path")
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                256,
                144,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.setText("🖼️ Generating...")
            self.preview_label.setStyleSheet("""
                background: #0f111a;
                border: 1px solid #2d3748;
                border-radius: 8px;
                color: #718096;
            """)

    def _on_approve(self):
        self._approved = self.approve_btn.isChecked()
        self.approve_btn.setText("✓" if self._approved else "Approve")
        self.approve_toggled.emit(self.scene_id, self._approved)

    def update_scene(self, scene_data: dict):
        """Update scene data and refresh display."""
        self.scene_data = scene_data
        self._load_preview()


class StoryboardGeneratorThread(QThread):
    """Background thread for storyboard generation."""

    progress = pyqtSignal(str)
    finished_storyboard = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        script: str,
        project_name: str,
        target_duration: int,
        generate_previews: bool = True,
    ):
        super().__init__()
        self.script = script
        self.project_name = project_name
        self.target_duration = target_duration
        self.generate_previews = generate_previews

    def run(self):
        try:
            self.progress.emit("Initializing AI director...")
            from ...ai.director import VideoDirector

            director = VideoDirector()

            self.progress.emit("Breaking script into scenes...")
            storyboard = director.generate_storyboard(
                script=self.script,
                project_name=self.project_name,
                target_duration=self.target_duration,
                generate_previews=self.generate_previews,
            )

            # Convert to dict for signal
            if storyboard:
                self.finished_storyboard.emit(storyboard.model_dump())
            else:
                self.error.emit("Failed to generate storyboard")

        except Exception as e:
            self.error.emit(str(e))


class StoryboardView(QWidget):
    """Main storyboard editor view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.storyboard = None
        self.scene_cards: list[SceneCard] = []
        self._generator_thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("🎬 Visual Storyboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")

        subtitle = QLabel("Preview and approve scenes before rendering")
        subtitle.setStyleSheet("color: #8892a6; font-size: 13px;")

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header.addLayout(title_layout)
        header.addStretch()

        # Action buttons
        self.generate_btn = QPushButton("✨ Generate Storyboard")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #7c3aed);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #667eea);
            }
            QPushButton:disabled {
                background: #4a5568;
            }
        """)
        self.generate_btn.clicked.connect(self._show_generate_dialog)

        self.render_btn = QPushButton("🎥 Render Video")
        self.render_btn.setEnabled(False)
        self.render_btn.setStyleSheet("""
            QPushButton {
                background: #48bb78;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #38a169; }
            QPushButton:disabled { background: #2d3748; color: #718096; }
        """)
        self.render_btn.clicked.connect(self._start_render)

        header.addWidget(self.generate_btn)
        header.addWidget(self.render_btn)
        layout.addLayout(header)

        # Progress bar (hidden by default)
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_label = QLabel("Generating storyboard...")
        self.progress_label.setStyleSheet("color: #a0aec0;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #2d3748;
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #7c3aed);
                border-radius: 4px;
            }
        """)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        self.progress_container.hide()
        layout.addWidget(self.progress_container)

        # Storyboard stats
        self.stats_container = QWidget()
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        self.total_scenes_lbl = QLabel("Scenes: 0")
        self.total_duration_lbl = QLabel("Duration: 0s")
        self.approved_lbl = QLabel("Approved: 0/0")

        for lbl in [self.total_scenes_lbl, self.total_duration_lbl, self.approved_lbl]:
            lbl.setStyleSheet("""
                background: #1e2740;
                padding: 8px 16px;
                border-radius: 6px;
                color: #a0aec0;
            """)
            stats_layout.addWidget(lbl)

        stats_layout.addStretch()
        self.stats_container.hide()
        layout.addWidget(self.stats_container)

        # Scene grid (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        self.scenes_container = QWidget()
        self.scenes_grid = QGridLayout(self.scenes_container)
        self.scenes_grid.setSpacing(16)
        self.scenes_grid.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.scenes_container)
        layout.addWidget(scroll, 1)

        # Empty state
        self.empty_state = QLabel(
            "Click 'Generate Storyboard' to create a visual preview"
        )
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("""
            color: #718096;
            font-size: 16px;
            padding: 60px;
        """)
        layout.addWidget(self.empty_state)

    def _show_generate_dialog(self):
        """Show dialog to input script and settings."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Storyboard")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background: #1a202c;
            }
            QLabel {
                color: white;
            }
            QTextEdit, QSpinBox {
                background: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 6px;
                color: white;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)

        # Script input
        script_lbl = QLabel("Video Script:")
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("Enter your video script here...")
        self.script_input.setMinimumHeight(200)

        # Duration
        duration_layout = QHBoxLayout()
        duration_lbl = QLabel("Target Duration (seconds):")
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(15, 300)
        self.duration_spin.setValue(60)
        duration_layout.addWidget(duration_lbl)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(script_lbl)
        layout.addWidget(self.script_input)
        layout.addLayout(duration_layout)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            script = self.script_input.toPlainText().strip()
            if script:
                self._generate_storyboard(script, self.duration_spin.value())

    def _generate_storyboard(self, script: str, target_duration: int):
        """Start storyboard generation in background."""
        self.generate_btn.setEnabled(False)
        self.progress_container.show()
        self.empty_state.hide()

        self._generator_thread = StoryboardGeneratorThread(
            script=script,
            project_name="Storyboard",
            target_duration=target_duration,
            generate_previews=True,
        )
        self._generator_thread.progress.connect(self._on_progress)
        self._generator_thread.finished_storyboard.connect(self._on_storyboard_ready)
        self._generator_thread.error.connect(self._on_error)
        self._generator_thread.start()

    def _on_progress(self, message: str):
        self.progress_label.setText(message)

    def _on_storyboard_ready(self, storyboard_data: dict):
        """Handle completed storyboard."""
        self.storyboard = storyboard_data
        self.progress_container.hide()
        self.generate_btn.setEnabled(True)
        self.stats_container.show()

        # Clear existing cards
        for card in self.scene_cards:
            card.deleteLater()
        self.scene_cards.clear()

        # Create scene cards
        scenes = storyboard_data.get("scenes", [])
        row, col = 0, 0
        max_cols = 4

        for scene in scenes:
            card = SceneCard(scene)
            card.regenerate_requested.connect(self._regenerate_scene)
            card.swap_stock_requested.connect(self._swap_with_stock)
            card.approve_toggled.connect(self._on_scene_approved)

            self.scenes_grid.addWidget(card, row, col)
            self.scene_cards.append(card)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Update stats
        self._update_stats()

    def _on_error(self, message: str):
        """Handle generation error."""
        self.progress_container.hide()
        self.generate_btn.setEnabled(True)
        self.empty_state.show()
        QMessageBox.critical(self, "Error", f"Storyboard generation failed:\n{message}")

    def _update_stats(self):
        """Update storyboard statistics."""
        if not self.storyboard:
            return

        scenes = self.storyboard.get("scenes", [])
        total = len(scenes)
        duration = sum(s.get("duration", 0) for s in scenes)
        approved = sum(1 for s in scenes if s.get("status") == "approved")

        self.total_scenes_lbl.setText(f"Scenes: {total}")
        self.total_duration_lbl.setText(f"Duration: {duration:.1f}s")
        self.approved_lbl.setText(f"Approved: {approved}/{total}")

        # Enable render if all approved
        self.render_btn.setEnabled(approved == total and total > 0)

    def _on_scene_approved(self, scene_id: int, approved: bool):
        """Handle scene approval toggle."""
        if self.storyboard:
            scenes = self.storyboard.get("scenes", [])
            for scene in scenes:
                if scene.get("id") == scene_id:
                    scene["status"] = "approved" if approved else "generated"
                    break
            self._update_stats()

    def _regenerate_scene(self, scene_id: int):
        """Regenerate a specific scene."""
        QMessageBox.information(
            self,
            "Regenerate",
            f"Regenerating scene {scene_id + 1}...\n(Full implementation pending)",
        )

    def _swap_with_stock(self, scene_id: int):
        """Replace scene with stock footage."""
        QMessageBox.information(
            self,
            "Stock Swap",
            f"Opening stock search for scene {scene_id + 1}...\n(Full implementation pending)",
        )

    def _start_render(self):
        """Start full video render."""
        if not self.storyboard:
            return

        reply = QMessageBox.question(
            self,
            "Render Video",
            "All scenes approved! Start rendering the final video?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self,
                "Rendering",
                "Video rendering started...\n(Integration with VideoProducer pending)",
            )
