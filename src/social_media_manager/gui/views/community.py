"""
Unified Engagement Inbox View.

Community management dashboard with:
- Multi-platform comment aggregation
- AI-powered reply suggestions
- One-click reply publishing
"""

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.community import CommunityManager
from ...database import Comment, DatabaseManager
from ..widgets.comment_card import CommentCard
from ..widgets.toasts import show_toast


class CommentFetchWorker(QThread):
    """Background worker to fetch comments from platforms."""

    finished = pyqtSignal(list)  # Emits list of Comment objects
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, manager: CommunityManager, platform: str | None = None) -> None:
        super().__init__()
        self.manager = manager
        self.platform = platform

    def run(self) -> None:
        try:
            self.progress.emit("Fetching comments...")
            # For now, use the database to get comments
            # In a full implementation, this would call platform APIs
            db = DatabaseManager()
            with db.get_session() as session:
                from sqlalchemy import select

                query = select(Comment).where(Comment.status != "ignored")
                if self.platform:
                    query = query.where(Comment.platform == self.platform)
                query = query.order_by(Comment.fetched_at.desc()).limit(50)

                result = session.execute(query)
                comments = result.scalars().all()

                # Convert to list of dicts for thread safety
                comment_data = []
                for c in comments:
                    comment_data.append(
                        {
                            "id": c.id,
                            "platform": c.platform,
                            "author": c.author or "Anonymous",
                            "text": c.text,
                            "status": c.status,
                            "reply_draft": c.reply_draft,
                            "fetched_at": c.fetched_at,
                        }
                    )

                self.finished.emit(comment_data)
        except Exception as e:
            logger.error(f"Failed to fetch comments: {e}")
            self.error.emit(str(e))


class ReplyGenerationWorker(QThread):
    """Background worker to generate AI replies."""

    finished = pyqtSignal(int, dict)  # Emits (comment_id, {tone: reply})
    error = pyqtSignal(int, str)

    def __init__(
        self, manager: CommunityManager, comment_id: int, comment_text: str
    ) -> None:
        super().__init__()
        self.manager = manager
        self.comment_id = comment_id
        self.comment_text = comment_text

    def run(self) -> None:
        try:
            replies = {}
            tones = ["grateful", "witty", "professional"]

            for tone in tones:
                prompt = self._build_prompt(tone)
                reply = self.manager.brain.think(prompt)
                if reply:
                    replies[tone] = reply.strip()

            self.finished.emit(self.comment_id, replies)
        except Exception as e:
            logger.error(f"Failed to generate replies: {e}")
            self.error.emit(self.comment_id, str(e))

    def _build_prompt(self, tone: str) -> str:
        """Build prompt for reply generation."""
        tone_instructions = {
            "grateful": "Write a warm, grateful response expressing appreciation.",
            "witty": "Write a clever, witty response that's engaging but professional.",
            "professional": "Write a formal, professional response.",
        }
        instruction = tone_instructions.get(tone, "Write a helpful response.")

        return f"""You are replying to a social media comment. Keep it brief (1-2 sentences).

Comment: "{self.comment_text}"

{instruction}

Reply:"""


class CommunityView(QWidget):
    """
    Unified Engagement Inbox for community management.

    Features:
    - Multi-platform comment aggregation
    - Platform filtering
    - AI-powered reply generation
    - One-click reply publishing
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager: CommunityManager | None = None
        self._comment_cards: dict[int, CommentCard] = {}
        self._workers: list[QThread] = []
        self._current_platform: str | None = None
        self._comments_data: list[dict] = []
        self._setup_ui()
        # Defer loading to avoid blocking on startup
        self._loaded = False

    def showEvent(self, event) -> None:
        """Load comments when view becomes visible."""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            self._load_comments()

    def _get_manager(self) -> CommunityManager:
        """Lazy-load CommunityManager."""
        if self._manager is None:
            self._manager = CommunityManager()
        return self._manager

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("💬 Engagement Inbox")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_comments)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a6a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a5a7a;
            }
        """)
        header_layout.addWidget(refresh_btn)

        # Sync platforms button
        sync_btn = QPushButton("📡 Sync Platforms")
        sync_btn.clicked.connect(self._sync_platforms)
        sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        header_layout.addWidget(sync_btn)

        layout.addLayout(header_layout)

        # Stats bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)

        self.pending_label = QLabel("⏳ Pending: 0")
        self.pending_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        stats_layout.addWidget(self.pending_label)

        self.replied_label = QLabel("✅ Replied: 0")
        self.replied_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        stats_layout.addWidget(self.replied_label)

        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # Platform filter tabs
        filter_layout = QHBoxLayout()

        filter_label = QLabel("Platform:")
        filter_label.setStyleSheet("color: #888888;")
        filter_layout.addWidget(filter_label)

        self.platform_filter = QComboBox()
        self.platform_filter.addItems(
            [
                "📬 All Platforms",
                "📺 YouTube",
                "📷 Instagram",
                "💼 LinkedIn",
                "🎵 TikTok",
            ]
        )
        self.platform_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.platform_filter.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #4a4a6a;
            }
        """)
        filter_layout.addWidget(self.platform_filter)

        filter_layout.addStretch()

        # Status filter
        status_label = QLabel("Status:")
        status_label.setStyleSheet("color: #888888;")
        filter_layout.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Replied", "Ignored"])
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        self.status_filter.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        filter_layout.addWidget(self.status_filter)

        layout.addLayout(filter_layout)

        # Comments scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.comments_container = QWidget()
        self.comments_layout = QVBoxLayout(self.comments_container)
        self.comments_layout.setContentsMargins(0, 0, 0, 0)
        self.comments_layout.setSpacing(12)
        self.comments_layout.addStretch()

        scroll.setWidget(self.comments_container)
        layout.addWidget(scroll)

        # Loading indicator
        self.loading_label = QLabel("Loading comments...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #888888; font-size: 14px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Empty state
        self.empty_label = QLabel(
            "📭 No comments yet!\n\nSync with your platforms to see comments here."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #666666;
            font-size: 14px;
            padding: 40px;
        """)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def _on_filter_changed(self, index: int) -> None:
        """Handle platform filter change."""
        platforms = [None, "youtube", "instagram", "linkedin", "tiktok"]
        self._current_platform = platforms[index] if index < len(platforms) else None
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply platform and status filters to displayed comments."""
        status_filter = self.status_filter.currentText().lower()
        if status_filter == "all":
            status_filter = None

        # Filter cached data
        filtered = []
        for c in self._comments_data:
            if (
                self._current_platform
                and c["platform"].lower() != self._current_platform
            ):
                continue
            if status_filter and c["status"] != status_filter:
                continue
            filtered.append(c)

        self._display_comments(filtered)

    def _load_comments(self) -> None:
        """Load comments from database/platforms."""
        self.loading_label.setVisible(True)
        self.empty_label.setVisible(False)

        worker = CommentFetchWorker(self._get_manager(), self._current_platform)
        worker.finished.connect(self._on_comments_loaded)
        worker.error.connect(self._on_comments_error)
        self._workers.append(worker)
        worker.start()

    def _on_comments_loaded(self, comments: list[dict]) -> None:
        """Handle loaded comments."""
        self.loading_label.setVisible(False)
        self._comments_data = comments

        if not comments:
            self.empty_label.setVisible(True)
            # Add mock data for demo purposes if database is empty
            self._add_mock_comments()
            return

        self._apply_filters()
        self._update_stats()

    def _add_mock_comments(self) -> None:
        """Add mock comments for demonstration."""
        mock_comments = [
            {
                "id": -1,
                "platform": "youtube",
                "author": "TechEnthusiast42",
                "text": "This is amazing content! Can you do a tutorial on advanced features?",
                "status": "pending",
                "reply_draft": None,
                "fetched_at": "2 hours ago",
            },
            {
                "id": -2,
                "platform": "instagram",
                "author": "CreativeMinds",
                "text": "Love the aesthetic! What camera do you use? 📸",
                "status": "pending",
                "reply_draft": None,
                "fetched_at": "4 hours ago",
            },
            {
                "id": -3,
                "platform": "linkedin",
                "author": "John Smith, Product Manager",
                "text": "Great insights on the industry trends. Would love to connect!",
                "status": "pending",
                "reply_draft": None,
                "fetched_at": "1 day ago",
            },
        ]
        self._comments_data = mock_comments
        self._display_comments(mock_comments)
        self.empty_label.setVisible(False)
        self._update_stats()

    def _on_comments_error(self, error: str) -> None:
        """Handle comment loading error."""
        self.loading_label.setVisible(False)
        show_toast(self, f"Failed to load comments: {error}", "error")
        # Show mock data as fallback
        self._add_mock_comments()

    def _display_comments(self, comments: list[dict]) -> None:
        """Display comment cards."""
        # Clear existing cards
        self._clear_comments()

        for c in comments:
            card = CommentCard(
                comment_id=c["id"],
                author=c["author"],
                text=c["text"],
                platform=c["platform"],
                timestamp=c.get("fetched_at", ""),
                status=c["status"],
            )
            card.reply_custom.connect(self._generate_replies)
            card.reply_selected.connect(self._send_reply)
            card.ignored.connect(self._ignore_comment)

            self._comment_cards[c["id"]] = card
            # Insert before stretch
            self.comments_layout.insertWidget(self.comments_layout.count() - 1, card)

    def _clear_comments(self) -> None:
        """Clear all comment cards."""
        for card in self._comment_cards.values():
            card.deleteLater()
        self._comment_cards.clear()

    def _update_stats(self) -> None:
        """Update the stats bar."""
        pending = sum(1 for c in self._comments_data if c["status"] == "pending")
        replied = sum(1 for c in self._comments_data if c["status"] == "replied")

        self.pending_label.setText(f"⏳ Pending: {pending}")
        self.replied_label.setText(f"✅ Replied: {replied}")

    def _generate_replies(self, comment_id: int) -> None:
        """Generate AI replies for a comment."""
        card = self._comment_cards.get(comment_id)
        if not card:
            return

        # Find the comment text
        comment_text = ""
        for c in self._comments_data:
            if c["id"] == comment_id:
                comment_text = c["text"]
                break

        if not comment_text:
            return

        show_toast(self, "Generating AI replies...", "info", 2000)

        worker = ReplyGenerationWorker(self._get_manager(), comment_id, comment_text)
        worker.finished.connect(self._on_replies_generated)
        worker.error.connect(self._on_replies_error)
        self._workers.append(worker)
        worker.start()

    def _on_replies_generated(self, comment_id: int, replies: dict) -> None:
        """Handle generated replies."""
        card = self._comment_cards.get(comment_id)
        if card and replies:
            card.set_reply_options(replies)
            show_toast(self, "AI replies generated!", "success")

    def _on_replies_error(self, comment_id: int, error: str) -> None:
        """Handle reply generation error."""
        show_toast(self, f"Failed to generate replies: {error}", "error")

    def _send_reply(self, comment_id: int, reply_text: str) -> None:
        """Send a reply to a comment."""
        # In real implementation, this would call the platform API
        logger.info(f"Sending reply to comment {comment_id}: {reply_text[:50]}...")

        card = self._comment_cards.get(comment_id)
        if card:
            card.set_status("replied")

        # Update in cached data
        for c in self._comments_data:
            if c["id"] == comment_id:
                c["status"] = "replied"
                c["reply_draft"] = reply_text
                break

        self._update_stats()
        show_toast(self, "Reply sent successfully!", "success")

    def _ignore_comment(self, comment_id: int) -> None:
        """Mark a comment as ignored."""
        card = self._comment_cards.get(comment_id)
        if card:
            card.set_status("ignored")

        # Update in cached data
        for c in self._comments_data:
            if c["id"] == comment_id:
                c["status"] = "ignored"
                break

        self._update_stats()
        show_toast(self, "Comment ignored", "info")

    def _sync_platforms(self) -> None:
        """Trigger platform sync (placeholder for OAuth flow)."""
        show_toast(
            self,
            "Platform sync requires OAuth setup in Settings → Connections",
            "warning",
            duration_ms=4000,
        )
