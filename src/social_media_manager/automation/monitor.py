import logging
import time
import traceback
from typing import Any

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..config import config
from ..core.orchestrator import SocialMediaManager

logger = logging.getLogger(__name__)


class Handler(FileSystemEventHandler):
    """
    File system event handler for the watchdog observer.

    Triggers video processing when a new video file is created in the watched directory.

    Attributes:
        manager (SocialMediaManager): The main orchestrator instance.
        processing (bool): Flag to indicate if a file is currently being processed.
    """

    def __init__(self) -> None:
        self.manager = SocialMediaManager()
        self.processing: bool = False

    def on_created(self, event: Any) -> None:
        if not event.src_path.endswith((".mp4", ".mov")) or self.processing:
            return
        self.processing = True
        time.sleep(2)
        try:
            self.manager.process_video(event.src_path)
        except FileNotFoundError as e:
            logging.error(f"Auto-process failed (file missing): {e}")
        except PermissionError as e:
            logging.error(f"Auto-process failed (access denied): {e}")
        except OSError as e:
            logging.error(f"Auto-process failed (I/O error): {e}")
        except Exception as e:
            logging.error(f"Auto-process unexpected error ({type(e).__name__}): {e}")
            logging.debug(traceback.format_exc())
        finally:
            self.processing = False


def start_watchdog() -> None:
    """
    Start the directory monitoring watchdog.

    Continuously watches the configured 'watch_folder' for new video files
    and processes them automatically using the `Handler`.
    """
    path = config.WATCH_FOLDER
    path.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(Handler(), str(path), recursive=False)
    observer.start()
    logging.info(f"🐶 Watchdog watching: {path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
