import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


def test_voxcpm():
    """Test VoxCPM TTS engine."""
    print("Testing VoxCPM TTS...")

    try:
        from social_media_manager.ai.voxcpm_engine import VoxCPMEngine, is_available
    except ImportError as e:
        print(f"❌ Failed to import VoxCPM engine: {e}")
        return

    if not is_available():
        print("❌ VoxCPM is not available. Run: pip install voxcpm")
        return

    engine = VoxCPMEngine()
    print(f"VoxCPM available: {engine.available}")
    print(f"Available voices: {engine.list_voices()}")

    # Test basic TTS
    text = "Hello, this is a test of the VoxCPM Text to Speech system."
    print(f"Generating audio for: '{text}'")

    output_path = Path("test_voxcpm_output.wav")
    result = engine.generate(text, output_path=output_path)

    if result and Path(result).exists():
        print(f"✅ Audio generated successfully at: {result}")
        print(f"File size: {Path(result).stat().st_size} bytes")
        # Clean up
        Path(result).unlink()
    else:
        print("❌ Audio generation failed.")


def test_tts_generator():
    """Test backwards-compatible TTSGenerator (ChatterboxGenerator alias)."""
    print("\nTesting TTSGenerator (ChatterboxGenerator alias)...")

    try:
        from social_media_manager.ai.audio_generator import (
            ChatterboxGenerator,
            TTSGenerator,
        )
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return

    # Check alias works
    assert TTSGenerator is not None
    assert ChatterboxGenerator is TTSGenerator
    print("✅ ChatterboxGenerator alias works")

    generator = TTSGenerator()
    print(f"TTSGenerator available: {generator.available}")


if __name__ == "__main__":
    test_voxcpm()
    test_tts_generator()
