"""
System Health Monitor for AgencyOS.

Monitors hardware resources to prevent crashes from running
multiple heavy AI models simultaneously.

Features:
- GPU VRAM usage monitoring (NVIDIA)
- CPU/RAM usage
- Active AI models tracking
- Resource reservation system
"""

import subprocess
import traceback
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger


@dataclass
class GPUInfo:
    """GPU information."""

    name: str
    index: int
    memory_total: int  # MB
    memory_used: int  # MB
    memory_free: int  # MB
    utilization: int  # Percentage
    temperature: int | None  # Celsius

    @property
    def memory_percent(self) -> float:
        """Memory usage percentage."""
        if self.memory_total == 0:
            return 0.0
        return (self.memory_used / self.memory_total) * 100

    @property
    def is_critical(self) -> bool:
        """Check if memory is critically low (<500MB free)."""
        return self.memory_free < 500

    @property
    def is_warning(self) -> bool:
        """Check if memory is getting low (<1GB free)."""
        return self.memory_free < 1024

    def can_fit(self, model_mb: int) -> bool:
        """Check if a model can fit in available memory."""
        # Leave 500MB buffer
        return self.memory_free - 500 >= model_mb


@dataclass
class SystemInfo:
    """System resource information."""

    cpu_percent: float
    ram_total: int  # MB
    ram_used: int  # MB
    ram_free: int  # MB
    ram_percent: float
    gpus: list[GPUInfo] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def has_gpu(self) -> bool:
        return len(self.gpus) > 0

    @property
    def primary_gpu(self) -> GPUInfo | None:
        return self.gpus[0] if self.gpus else None


# Estimated VRAM requirements for common models (in MB)
MODEL_VRAM = {
    # LLMs
    "llama3.2:3b": 2500,
    "llama3.1:8b": 5000,
    "mistral:7b": 4500,
    "llama3.2:1b": 1500,
    # Whisper
    "whisper-large-v3": 3000,
    "whisper-medium": 1500,
    "whisper-small": 800,
    "whisper-base": 400,
    # MusicGen
    "musicgen-small": 2000,
    "musicgen-medium": 3500,
    "musicgen-large": 5000,
    # Image models
    "clip-vit-b-32": 400,
    "real-esrgan": 500,
    "gfpgan": 800,
    "rembg": 1000,
    # RVC
    "rvc-inference": 1500,
    # SadTalker
    "sadtalker": 2500,
}


class SystemMonitor:
    """
    Monitor system resources and manage AI model scheduling.

    Example:
        monitor = SystemMonitor()

        # Get current system status
        info = monitor.get_status()
        print(f"GPU: {info.primary_gpu.memory_used}/{info.primary_gpu.memory_total}MB")

        # Check if we can run a model
        if monitor.can_run_model("whisper-large-v3"):
            print("Safe to run Whisper!")

        # Get recommendations
        rec = monitor.get_recommendations()
        print(rec)
    """

    def __init__(self):
        self._active_models: dict[str, int] = {}  # model -> estimated VRAM
        self._nvidia_available = self._check_nvidia()

        logger.info(f"🖥️ System Monitor initialized (NVIDIA: {self._nvidia_available})")

    def _check_nvidia(self) -> bool:
        """Check if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_gpu_info(self) -> list[GPUInfo]:
        """Get GPU information using nvidia-smi."""
        if not self._nvidia_available:
            return []

        try:
            # Query GPU info
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    try:
                        gpus.append(
                            GPUInfo(
                                index=int(parts[0]),
                                name=parts[1],
                                memory_total=int(parts[2]),
                                memory_used=int(parts[3]),
                                memory_free=int(parts[4]),
                                utilization=int(parts[5]) if parts[5] != "[N/A]" else 0,
                                temperature=int(parts[6])
                                if len(parts) > 6 and parts[6] != "[N/A]"
                                else None,
                            )
                        )
                    except (ValueError, IndexError):
                        continue

            return gpus

        except subprocess.TimeoutExpired:
            logger.warning("GPU info query timed out")
            return []
        except subprocess.SubprocessError as e:
            logger.warning(f"GPU info subprocess error: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to get GPU info ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return []

    def get_cpu_ram_info(self) -> tuple[float, int, int, int, float]:
        """Get CPU and RAM info."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()

            return (
                cpu_percent,
                ram.total // (1024 * 1024),  # Total MB
                ram.used // (1024 * 1024),  # Used MB
                ram.available // (1024 * 1024),  # Free MB
                ram.percent,
            )
        except ImportError:
            # Fallback without psutil
            try:
                with open("/proc/meminfo") as f:
                    lines = f.readlines()

                mem_info = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1]) // 1024  # Convert to MB
                        mem_info[key] = value

                total = mem_info.get("MemTotal", 0)
                free = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
                used = total - free
                percent = (used / total * 100) if total > 0 else 0

                # CPU from /proc/stat (simplified)
                cpu_percent = 0.0
                try:
                    with open("/proc/stat") as f:
                        cpu_line = f.readline()
                    parts = cpu_line.split()
                    if parts[0] == "cpu":
                        total_time = sum(int(p) for p in parts[1:])
                        idle_time = int(parts[4])
                        cpu_percent = ((total_time - idle_time) / total_time) * 100
                except Exception:
                    pass

                return (cpu_percent, total, used, free, percent)

            except Exception:
                return (0.0, 0, 0, 0, 0.0)

    def get_status(self) -> SystemInfo:
        """Get current system status."""
        cpu, ram_total, ram_used, ram_free, ram_percent = self.get_cpu_ram_info()
        gpus = self.get_gpu_info()

        return SystemInfo(
            cpu_percent=cpu,
            ram_total=ram_total,
            ram_used=ram_used,
            ram_free=ram_free,
            ram_percent=ram_percent,
            gpus=gpus,
        )

    def can_run_model(
        self,
        model: str,
        required_vram: int | None = None,
    ) -> bool:
        """
        Check if we have enough VRAM to run a model.

        Args:
            model: Model name (from MODEL_VRAM dict or custom).
            required_vram: Override VRAM requirement in MB.

        Returns:
            True if model can be safely loaded.
        """
        vram_needed = required_vram or MODEL_VRAM.get(model, 1000)

        gpus = self.get_gpu_info()
        if not gpus:
            # No GPU, assume CPU-only mode works
            return True

        primary_gpu = gpus[0]
        return primary_gpu.can_fit(vram_needed)

    def get_runnable_models(self) -> list[str]:
        """Get list of models that can currently be run."""
        gpus = self.get_gpu_info()
        if not gpus:
            return list(MODEL_VRAM.keys())

        available_vram = gpus[0].memory_free - 500  # 500MB buffer

        runnable = []
        for model, vram in MODEL_VRAM.items():
            if vram <= available_vram:
                runnable.append(model)

        return runnable

    def get_recommendations(self) -> dict:
        """Get recommendations for what can be safely run."""
        status = self.get_status()

        rec = {
            "can_run_llm": False,
            "can_run_whisper": False,
            "can_run_musicgen": False,
            "can_run_image_models": False,
            "can_run_voice_clone": False,
            "warnings": [],
            "suggestions": [],
        }

        if not status.has_gpu:
            rec["warnings"].append(
                "No NVIDIA GPU detected - AI models will run on CPU (slower)"
            )
            rec["can_run_llm"] = True  # Ollama handles CPU fallback
            return rec

        gpu = status.primary_gpu
        free_vram = gpu.memory_free

        # Check what we can run
        if free_vram >= 2500:
            rec["can_run_llm"] = True
        if free_vram >= 3000:
            rec["can_run_whisper"] = True
        if free_vram >= 2000:
            rec["can_run_musicgen"] = True
        if free_vram >= 1000:
            rec["can_run_image_models"] = True
        if free_vram >= 1500:
            rec["can_run_voice_clone"] = True

        # Warnings
        if gpu.is_critical:
            rec["warnings"].append(
                f"⚠️ CRITICAL: Only {free_vram}MB VRAM free! Close applications to prevent crashes."
            )
        elif gpu.is_warning:
            rec["warnings"].append(
                f"⚠️ Low VRAM: {free_vram}MB free. Avoid running multiple AI models."
            )

        if gpu.temperature and gpu.temperature > 80:
            rec["warnings"].append(f"🌡️ GPU temperature high: {gpu.temperature}°C")

        # Suggestions
        if free_vram < 2000:
            rec["suggestions"].append(
                "Consider using smaller models (whisper-small, llama3.2:1b)"
            )

        if not rec["can_run_llm"] and not rec["can_run_whisper"]:
            rec["suggestions"].append("Close other GPU applications to free VRAM")

        return rec

    def register_model(self, model: str, vram: int | None = None):
        """Register a model as currently active."""
        vram_used = vram or MODEL_VRAM.get(model, 1000)
        self._active_models[model] = vram_used
        logger.info(f"📊 Registered active model: {model} (~{vram_used}MB)")

    def unregister_model(self, model: str):
        """Unregister a model when it's unloaded."""
        if model in self._active_models:
            del self._active_models[model]
            logger.info(f"📊 Unregistered model: {model}")

    def get_active_models(self) -> dict[str, int]:
        """Get currently registered active models."""
        return self._active_models.copy()


# Singleton instance
_monitor: SystemMonitor | None = None


def get_monitor() -> SystemMonitor:
    """Get the singleton SystemMonitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor


def get_system_status() -> SystemInfo:
    """Quick function to get current system status."""
    return get_monitor().get_status()


def can_run_model(model: str) -> bool:
    """Quick function to check if a model can run."""
    return get_monitor().can_run_model(model)
