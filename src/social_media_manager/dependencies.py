"""
Centralized dependency checking for AgencyOS.

Checks all optional dependencies at startup instead of scattered
try/except ImportError blocks throughout the codebase. This allows
for early warning to users about disabled features.
"""

import importlib.util
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DependencyStatus:
    """Status of an optional dependency."""

    name: str
    available: bool
    feature: str
    install_hint: str
    version: str | None = None


@dataclass
class DependencyRegistry:
    """Registry of all optional dependencies and their status."""

    dependencies: dict[str, DependencyStatus] = field(default_factory=dict)
    checked: bool = False

    def is_available(self, name: str) -> bool:
        """Check if a dependency is available."""
        dep = self.dependencies.get(name)
        return dep.available if dep else False

    def get_missing(self) -> list[DependencyStatus]:
        """Get list of missing dependencies."""
        return [d for d in self.dependencies.values() if not d.available]

    def get_available(self) -> list[DependencyStatus]:
        """Get list of available dependencies."""
        return [d for d in self.dependencies.values() if d.available]


# Global registry singleton
_registry: DependencyRegistry | None = None


def _check_import(module_name: str) -> bool:
    """Check if a module can be imported using importlib.util.find_spec."""
    return importlib.util.find_spec(module_name) is not None


def check_dependencies() -> DependencyRegistry:
    """
    Check all optional dependencies and populate the registry.

    Should be called once at application startup.

    Returns:
        DependencyRegistry with status of all optional dependencies.
    """
    global _registry

    if _registry is not None and _registry.checked:
        return _registry

    _registry = DependencyRegistry()
    deps = _registry.dependencies

    # === LLM/AI Dependencies ===

    # LiteLLM - Multi-provider LLM support
    if _check_import("litellm"):
        import litellm

        deps["litellm"] = DependencyStatus(
            name="litellm",
            available=True,
            feature="Multi-LLM Provider Support",
            install_hint="pip install litellm",
            version=getattr(litellm, "__version__", None),
        )
    else:
        deps["litellm"] = DependencyStatus(
            name="litellm",
            available=False,
            feature="Multi-LLM Provider Support",
            install_hint="pip install litellm",
        )

    # Groq - Fast inference
    if _check_import("groq"):
        import groq

        deps["groq"] = DependencyStatus(
            name="groq",
            available=True,
            feature="Groq LLM Provider",
            install_hint="pip install groq",
            version=getattr(groq, "__version__", None),
        )
    else:
        deps["groq"] = DependencyStatus(
            name="groq",
            available=False,
            feature="Groq LLM Provider",
            install_hint="pip install groq",
        )

    # === Audio/Video Dependencies ===

    # VoxCPM - Text-to-speech with voice cloning
    deps["voxcpm"] = DependencyStatus(
        name="voxcpm",
        available=_check_import("voxcpm"),
        feature="Voice Generation (TTS + Voice Cloning)",
        install_hint="pip install voxcpm",
    )

    # MoviePy - Video editing
    if _check_import("moviepy"):
        import moviepy

        deps["moviepy"] = DependencyStatus(
            name="moviepy",
            available=True,
            feature="Video Processing",
            install_hint="pip install moviepy",
            version=getattr(moviepy, "__version__", None),
        )
    else:
        deps["moviepy"] = DependencyStatus(
            name="moviepy",
            available=False,
            feature="Video Processing",
            install_hint="pip install moviepy",
        )

    # OpenCV - Computer vision
    if _check_import("cv2"):
        import cv2

        deps["opencv"] = DependencyStatus(
            name="opencv-python",
            available=True,
            feature="Face Detection & Image Processing",
            install_hint="pip install opencv-python",
            version=cv2.__version__,
        )
    else:
        deps["opencv"] = DependencyStatus(
            name="opencv-python",
            available=False,
            feature="Face Detection & Image Processing",
            install_hint="pip install opencv-python",
        )

    # === AI Model Dependencies ===

    # Whisper - Speech-to-text
    deps["whisper"] = DependencyStatus(
        name="openai-whisper",
        available=_check_import("whisper"),
        feature="Audio Transcription",
        install_hint="pip install openai-whisper",
    )

    # Transformers - AI models
    if _check_import("transformers"):
        import transformers

        deps["transformers"] = DependencyStatus(
            name="transformers",
            available=True,
            feature="AI Models (MusicGen, etc.)",
            install_hint="pip install transformers",
            version=transformers.__version__,
        )
    else:
        deps["transformers"] = DependencyStatus(
            name="transformers",
            available=False,
            feature="AI Models (MusicGen, etc.)",
            install_hint="pip install transformers",
        )

    # Real-ESRGAN - Image upscaling
    deps["realesrgan"] = DependencyStatus(
        name="realesrgan",
        available=_check_import("realesrgan"),
        feature="AI Image Upscaling",
        install_hint="pip install realesrgan",
    )

    # === Web/Search Dependencies ===

    # DuckDuckGo Search
    deps["duckduckgo"] = DependencyStatus(
        name="duckduckgo-search",
        available=_check_import("duckduckgo_search"),
        feature="Web Search",
        install_hint="pip install duckduckgo-search",
    )

    # ChromaDB - Vector database
    if _check_import("chromadb"):
        import chromadb

        deps["chromadb"] = DependencyStatus(
            name="chromadb",
            available=True,
            feature="Knowledge Base (RAG)",
            install_hint="pip install chromadb",
            version=getattr(chromadb, "__version__", None),
        )
    else:
        deps["chromadb"] = DependencyStatus(
            name="chromadb",
            available=False,
            feature="Knowledge Base (RAG)",
            install_hint="pip install chromadb",
        )

    _registry.checked = True
    return _registry


def log_dependency_status() -> list[str]:
    """
    Log the status of all dependencies.

    Returns:
        List of names of missing dependencies.
    """
    registry = check_dependencies()
    missing = registry.get_missing()

    if missing:
        logger.warning("⚠️ Optional dependencies missing (some features disabled):")
        for dep in missing:
            logger.warning(f"   • {dep.name}: {dep.feature}")
            logger.warning(f"     Install: {dep.install_hint}")
    else:
        logger.info("✅ All optional dependencies available")

    return [d.name for d in missing]


def get_dependency_status() -> dict[str, bool]:
    """
    Get a simple dict of dependency name to availability status.

    Returns:
        Dict mapping dependency names to boolean availability.
    """
    registry = check_dependencies()
    return {name: dep.available for name, dep in registry.dependencies.items()}


# Convenience accessors for common checks
def is_tts_available() -> bool:
    """Check if text-to-speech is available."""
    return check_dependencies().is_available("voxcpm")


def is_litellm_available() -> bool:
    """Check if LiteLLM is available."""
    return check_dependencies().is_available("litellm")


def is_whisper_available() -> bool:
    """Check if Whisper transcription is available."""
    return check_dependencies().is_available("whisper")


def is_upscaling_available() -> bool:
    """Check if image upscaling is available."""
    return check_dependencies().is_available("realesrgan")
