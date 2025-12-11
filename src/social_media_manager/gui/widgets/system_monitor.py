"""
System Monitor Widget for the GUI.
Displays CPU, RAM, and GPU usage with visual progress bars.
"""

import subprocess

import psutil
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ResourceBar(QWidget):
    """A single resource monitor bar (e.g. CPU)."""

    def __init__(self, label: str, color: str = "#4F8BF9"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header (Label + Value)
        header_layout = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #a0a0a0; font-weight: bold;")
        self.value_label = QLabel("0%")
        self.value_label.setStyleSheet("color: #ffffff; font-weight: bold;")

        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        layout.addLayout(header_layout)

        # Progress Bar
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2d3748;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.bar)

    def update_value(self, percent: float, text: str = None):
        self.bar.setValue(int(percent))
        self.value_label.setText(text if text else f"{int(percent)}%")


class SystemMonitorWidget(QFrame):
    """Widget grouping multiple resource bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SystemMonitorWidget {
                background-color: #1a1a2e;
                border-radius: 12px;
                border: 1px solid #0f3460;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("🖥️ System Resources")
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #e94560; margin-bottom: 10px;"
        )
        layout.addWidget(title)

        # Bars
        self.cpu_bar = ResourceBar("CPU Usage", "#e94560")  # Red
        self.ram_bar = ResourceBar("RAM Usage", "#4F8BF9")  # Blue
        self.gpu_bar = ResourceBar("GPU VRAM (RTX 2060)", "#00C851")  # Green

        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.ram_bar)
        layout.addWidget(self.gpu_bar)
        layout.addStretch()

        # Update Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(2000)  # Update every 2s
        self._update_stats()

    def _update_stats(self):
        # CPU
        cpu = psutil.cpu_percent()
        self.cpu_bar.update_value(cpu)

        # RAM
        ram = psutil.virtual_memory()
        self.ram_bar.update_value(
            ram.percent, f"{ram.used // (1024**3)}GB / {ram.total // (1024**3)}GB"
        )

        # GPU (NVIDIA)
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total",
                    "--format=csv,nounits,noheader",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                used, total = map(int, result.stdout.strip().split(","))
                percent = (used / total) * 100
                self.gpu_bar.update_value(percent, f"{used}MB / {total}MB")
        except Exception:
            self.gpu_bar.update_value(0, "N/A")
