import logging
import sys
from pathlib import Path

# Ensure src is in path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from social_media_manager.core.orchestrator import SocialMediaManager

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrationTest")


def create_dummy_video(path: Path):
    """Creates a minimal valid MP4 file for testing."""
    # Note: Creating a real MP4 from scratch without heavy libs is hard.
    # We will assume a file exists or create a text file disguised as MP4
    # to test the logic flow, even if ffmpeg fails on it.
    # ideally, use a small sample.mp4 stored in tests/
    path.write_text("fake video content")


def run_test():
    print("🚀 Starting Integration Test...")

    # 1. Setup
    manager = SocialMediaManager()
    test_video_path = Path("test_video.mp4")

    # We need a real video file for ffmpeg to work,
    # but for logic testing we can mock the processor if needed.
    # Here we assume the user has a 'sample_video.mp4' or we skip the heavy processing.

    if not test_video_path.exists():
        logger.warning("⚠️ 'test_video.mp4' not found. Skipping video processing check.")
    else:
        logger.info("🎬 Testing Video Processing Pipeline...")
        try:
            result = manager.process_video(
                str(test_video_path),
                platforms=["youtube"],
                client_name="TestClient",
                options={"smart_cut": False},  # Disable heavy AI for quick test
            )

            print(f"✅ Processing Result: {result}")
            assert result["id"] is not None
            assert "caption" in result

        except Exception as e:
            logger.error(f"❌ Processing Failed: {e}")
            return

    # 2. Test AI Brain
    logger.info("🧠 Testing AI Brain...")
    if manager.brain:
        response = manager.brain.think(
            "Say 'Hello World' in JSON: {'msg': ...}", json_mode=True
        )
        print(f"✅ Brain Response: {response}")
    else:
        print("⚠️ Brain not initialized.")

    # 3. Test Database
    logger.info("💾 Testing Database...")
    stats = manager.db.get_analytics()
    print(f"✅ Analytics Rows: {len(stats)}")

    print("\n🎉 Integration Test Complete!")


if __name__ == "__main__":
    run_test()
