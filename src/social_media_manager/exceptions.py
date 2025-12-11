"""
Custom exceptions for the Social Media Manager.

Provides a hierarchy of domain-specific exceptions for better error handling
and debugging. Catching specific exceptions instead of generic Exception
makes debugging easier and prevents swallowing unintended errors.
"""


class SocialMediaManagerError(Exception):
    """Base exception for all application errors."""

    pass


class VideoProcessingError(SocialMediaManagerError):
    """Error during video processing operations."""

    pass


class VideoFileError(VideoProcessingError):
    """Error with video file access or format."""

    pass


class VideoCodecError(VideoProcessingError):
    """Error with video encoding/decoding."""

    pass


class AIGenerationError(SocialMediaManagerError):
    """Error during AI content generation."""

    pass


class LLMConnectionError(AIGenerationError):
    """Error connecting to LLM service."""

    pass


class LLMResponseError(AIGenerationError):
    """Invalid or unexpected response from LLM."""

    pass


class DependencyMissingError(SocialMediaManagerError):
    """Required dependency is not available."""

    dependency: str
    feature: str
    install_hint: str

    def __init__(self, dependency: str, feature: str, install_hint: str = ""):
        self.dependency = dependency
        self.feature = feature
        self.install_hint = install_hint
        message = f"Missing dependency '{dependency}' required for {feature}"
        if install_hint:
            message += f". Install with: {install_hint}"
        super().__init__(message)


class ConfigurationError(SocialMediaManagerError):
    """Error in application configuration."""

    pass


class DatabaseError(SocialMediaManagerError):
    """Error in database operations."""

    pass


class PlatformUploadError(SocialMediaManagerError):
    """Error uploading content to a platform."""

    pass
