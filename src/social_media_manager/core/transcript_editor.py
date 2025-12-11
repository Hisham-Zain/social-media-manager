"""
Transcript Editor for Text-Based Video Editing.

Edit video by editing text - words marked for deletion are cut from the video.
Leverages Whisper for word-level timestamps and MoviePy for video cutting.

Features:
- Word-to-timestamp mapping
- Edit tracking (keep/delete)
- Cut list generation for VideoProcessor
- Undo/redo support
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger


@dataclass
class WordSegment:
    """A single word with timing information and edit state."""

    word: str
    start: float
    end: float
    index: int
    state: Literal["keep", "delete", "pending"] = "pending"
    confidence: float = 1.0


@dataclass
class TranscriptDocument:
    """
    Complete transcript with edit state.

    Represents the entire video transcript with word-level
    edit capabilities.
    """

    video_path: str
    words: list[WordSegment] = field(default_factory=list)
    duration: float = 0.0
    _history: list[list[WordSegment]] = field(default_factory=list)
    _redo_stack: list[list[WordSegment]] = field(default_factory=list)

    def get_text(self) -> str:
        """Get full transcript text without timing info."""
        return " ".join(w.word for w in self.words)

    def get_kept_text(self) -> str:
        """Get only the kept words (not deleted)."""
        return " ".join(w.word for w in self.words if w.state != "delete")

    def get_deleted_text(self) -> str:
        """Get only the deleted words."""
        return " ".join(w.word for w in self.words if w.state == "delete")


class TranscriptEditor:
    """
    Edit video by editing transcript.

    The "Descript Killer" - mark words in the transcript for deletion,
    and the video will be automatically re-cut to exclude those segments.

    Example:
        editor = TranscriptEditor()
        doc = editor.transcribe("video.mp4")

        # Mark words 5-10 for deletion
        editor.mark_for_deletion([5, 6, 7, 8, 9, 10])

        # Generate cut list for VideoProcessor
        cuts = editor.generate_cut_list()

        # Apply cuts and export
        output = editor.export_edited_video()
    """

    def __init__(self) -> None:
        self._document: TranscriptDocument | None = None
        self._transcriber: object | None = None

    @property
    def transcriber(self):
        """Lazy-load DynamicCaptions transcriber."""
        if self._transcriber is None:
            try:
                from .dynamic_captions import DynamicCaptions

                captions = DynamicCaptions()
                self._transcriber = captions
            except Exception as e:
                logger.warning(f"DynamicCaptions not available: {e}")
                self._transcriber = None
        return self._transcriber

    def transcribe(self, video_path: str) -> TranscriptDocument:
        """
        Transcribe a video and create an editable document.

        Args:
            video_path: Path to video file.

        Returns:
            TranscriptDocument with word-level segments.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"🗣️ Transcribing {path.name} for text-based editing...")

        words = []
        duration = 0.0

        try:
            if self.transcriber is not None:
                # Use DynamicCaptions for word-level timestamps
                segments = self.transcriber.transcribe_with_words(str(video_path))

                idx = 0
                for segment in segments:
                    for word_timing in segment.words:
                        words.append(
                            WordSegment(
                                word=word_timing.word,
                                start=word_timing.start,
                                end=word_timing.end,
                                index=idx,
                                confidence=getattr(word_timing, "confidence", 1.0),
                            )
                        )
                        idx += 1
                        duration = max(duration, word_timing.end)
            else:
                # Fallback: use WhisperTranscriber for segment-level
                from ..ai.transcriber import WhisperTranscriber

                transcriber = WhisperTranscriber()
                srt_path = transcriber.generate_srt(str(video_path))

                if srt_path:
                    # Parse SRT and create approximate word segments
                    words, duration = self._parse_srt_to_words(srt_path)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Failed to transcribe {video_path}: {e}") from e

        self._document = TranscriptDocument(
            video_path=str(video_path),
            words=words,
            duration=duration,
        )

        logger.info(f"✅ Transcription complete: {len(words)} words, {duration:.1f}s")
        return self._document

    def _parse_srt_to_words(self, srt_path: str) -> tuple[list[WordSegment], float]:
        """
        Parse SRT and split into word-level segments.

        This is an approximation - distributes time evenly across words.
        """
        words = []
        duration = 0.0
        idx = 0

        with open(srt_path, encoding="utf-8") as f:
            content = f.read()

        import re

        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for _, start_str, end_str, text in matches:
            start = self._parse_srt_time(start_str)
            end = self._parse_srt_time(end_str)

            # Split text into words
            text_words = text.strip().split()
            if not text_words:
                continue

            # Distribute time evenly across words
            word_duration = (end - start) / len(text_words)

            for i, word in enumerate(text_words):
                word_start = start + (i * word_duration)
                word_end = word_start + word_duration

                words.append(
                    WordSegment(
                        word=word,
                        start=word_start,
                        end=word_end,
                        index=idx,
                    )
                )
                idx += 1
                duration = max(duration, word_end)

        return words, duration

    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT timestamp to seconds."""
        time_str = time_str.replace(",", ".")
        parts = time_str.split(":")
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def get_document(self) -> TranscriptDocument | None:
        """Get the current transcript document."""
        return self._document

    def mark_for_deletion(self, indices: list[int]) -> None:
        """
        Mark words at given indices for deletion.

        Args:
            indices: List of word indices to delete.
        """
        if not self._document:
            raise RuntimeError("No document loaded. Call transcribe() first.")

        # Save state for undo
        self._save_state()

        for idx in indices:
            if 0 <= idx < len(self._document.words):
                self._document.words[idx].state = "delete"

        logger.debug(f"Marked {len(indices)} words for deletion")

    def mark_for_keep(self, indices: list[int]) -> None:
        """
        Mark words at given indices to keep (restore from deletion).

        Args:
            indices: List of word indices to keep.
        """
        if not self._document:
            raise RuntimeError("No document loaded. Call transcribe() first.")

        self._save_state()

        for idx in indices:
            if 0 <= idx < len(self._document.words):
                self._document.words[idx].state = "keep"

        logger.debug(f"Marked {len(indices)} words to keep")

    def mark_range_for_deletion(self, start_idx: int, end_idx: int) -> None:
        """Mark a contiguous range of words for deletion."""
        self.mark_for_deletion(list(range(start_idx, end_idx + 1)))

    def mark_range_for_keep(self, start_idx: int, end_idx: int) -> None:
        """Mark a contiguous range of words to keep."""
        self.mark_for_keep(list(range(start_idx, end_idx + 1)))

    def delete_all_with_text(self, text: str) -> int:
        """
        Delete all words matching the given text.

        Args:
            text: Word text to match (case-insensitive).

        Returns:
            Number of words deleted.
        """
        if not self._document:
            return 0

        self._save_state()

        count = 0
        text_lower = text.lower()
        for word in self._document.words:
            if word.word.lower().strip(".,!?;:") == text_lower:
                word.state = "delete"
                count += 1

        return count

    def _save_state(self) -> None:
        """Save current state for undo."""
        if self._document:
            state_copy = [
                WordSegment(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    index=w.index,
                    state=w.state,
                    confidence=w.confidence,
                )
                for w in self._document.words
            ]
            self._document._history.append(state_copy)
            self._document._redo_stack.clear()

    def undo(self) -> bool:
        """
        Undo the last edit.

        Returns:
            True if undo was successful.
        """
        if not self._document or not self._document._history:
            return False

        # Save current state to redo stack
        current_copy = [
            WordSegment(
                word=w.word,
                start=w.start,
                end=w.end,
                index=w.index,
                state=w.state,
                confidence=w.confidence,
            )
            for w in self._document.words
        ]
        self._document._redo_stack.append(current_copy)

        # Restore previous state
        self._document.words = self._document._history.pop()
        return True

    def redo(self) -> bool:
        """
        Redo the last undone edit.

        Returns:
            True if redo was successful.
        """
        if not self._document or not self._document._redo_stack:
            return False

        # Save current state to history
        current_copy = [
            WordSegment(
                word=w.word,
                start=w.start,
                end=w.end,
                index=w.index,
                state=w.state,
                confidence=w.confidence,
            )
            for w in self._document.words
        ]
        self._document._history.append(current_copy)

        # Restore redo state
        self._document.words = self._document._redo_stack.pop()
        return True

    def generate_cut_list(self) -> list[tuple[float, float]]:
        """
        Generate a list of segments to KEEP (exclude deleted words).

        Returns:
            List of (start, end) tuples representing video segments to keep.
        """
        if not self._document or not self._document.words:
            return []

        segments = []
        current_start = None
        current_end = None

        for word in self._document.words:
            if word.state != "delete":
                # Start or extend a segment
                if current_start is None:
                    current_start = word.start
                current_end = word.end
            else:
                # End current segment if exists
                if current_start is not None:
                    segments.append((current_start, current_end))
                    current_start = None
                    current_end = None

        # Don't forget the last segment
        if current_start is not None:
            segments.append((current_start, current_end))

        return segments

    def get_edit_stats(self) -> dict:
        """
        Get statistics about current edits.

        Returns:
            Dict with counts and percentages.
        """
        if not self._document:
            return {}

        total = len(self._document.words)
        deleted = sum(1 for w in self._document.words if w.state == "delete")
        kept = sum(1 for w in self._document.words if w.state == "keep")
        pending = total - deleted - kept

        original_duration = self._document.duration
        cut_list = self.generate_cut_list()
        new_duration = sum(end - start for start, end in cut_list)

        return {
            "total_words": total,
            "deleted_words": deleted,
            "kept_words": kept,
            "pending_words": pending,
            "deleted_percent": (deleted / total * 100) if total else 0,
            "original_duration": original_duration,
            "new_duration": new_duration,
            "time_removed": original_duration - new_duration,
        }

    def export_edited_video(self, output_path: str | None = None) -> str:
        """
        Apply transcript edits and export the video.

        Args:
            output_path: Optional output path. Auto-generated if not provided.

        Returns:
            Path to the edited video.
        """
        if not self._document:
            raise RuntimeError("No document loaded. Call transcribe() first.")

        cut_list = self.generate_cut_list()
        if not cut_list:
            logger.warning("No segments to keep - entire video would be deleted!")
            raise ValueError("Cannot export: all content marked for deletion.")

        from .processor import VideoProcessor

        processor = VideoProcessor()

        video_path = self._document.video_path
        if output_path is None:
            path = Path(video_path)
            output_path = str(path.parent / f"{path.stem}_edited{path.suffix}")

        logger.info("✂️ Applying transcript edits to video...")
        logger.info(f"   Keeping {len(cut_list)} segments")

        result = processor.apply_transcript_cuts(video_path, cut_list, output_path)

        logger.info(f"✅ Edited video saved: {result}")
        return result


# Convenience function
def edit_video_by_transcript(
    video_path: str,
    delete_words: list[str] | None = None,
    delete_indices: list[int] | None = None,
) -> str:
    """
    Quick function to edit a video by transcript.

    Args:
        video_path: Path to video.
        delete_words: List of words to delete (all occurrences).
        delete_indices: List of word indices to delete.

    Returns:
        Path to edited video.
    """
    editor = TranscriptEditor()
    editor.transcribe(video_path)

    if delete_words:
        for word in delete_words:
            editor.delete_all_with_text(word)

    if delete_indices:
        editor.mark_for_deletion(delete_indices)

    return editor.export_edited_video()
