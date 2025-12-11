import logging
import os
from contextlib import contextmanager
from datetime import datetime

import pandas as pd
import sqlalchemy.exc
from sqlalchemy import Float, ForeignKey, Integer, String, create_engine, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import config

logger = logging.getLogger(__name__)


# --- ORM Base & Models ---
class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)
    duration: Mapped[float] = mapped_column(Float)
    style: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )


class PostedContent(Base):
    __tablename__ = "posted_content"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    platform: Mapped[str] = mapped_column(String)
    platform_id: Mapped[str] = mapped_column(String)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    posted_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String)
    platform_comment_id: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(String)
    sentiment: Mapped[str] = mapped_column(String, default="neutral")
    reply_draft: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    fetched_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )


class Project(Base):
    """
    Project model for storing draft states of content creation.

    Stores all components needed to resume editing:
    - Script/caption text
    - Audio file paths
    - Video clip paths
    - Thumbnail path
    - Project settings and metadata
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, default="draft"
    )  # draft, rendering, complete

    # Content
    script: Mapped[str | None] = mapped_column(String, nullable=True)
    caption: Mapped[str | None] = mapped_column(String, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(String, nullable=True)

    # File paths (JSON arrays stored as strings)
    audio_paths: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON list
    video_paths: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON list
    image_paths: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON list
    thumbnail_path: Mapped[str | None] = mapped_column(String, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Settings (JSON object stored as string)
    settings: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON

    # Metadata
    platform: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # youtube, tiktok, etc
    aspect_ratio: Mapped[str] = mapped_column(String, default="16:9")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )


class Asset(Base):
    """
    Asset model for Smart Asset Management (The Vault).

    Stores metadata about all content assets with:
    - Content hashing for deduplication
    - Tags for organization
    - CLIP embeddings for semantic search
    - Project associations
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)

    # File info
    filename: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String, unique=True)
    asset_type: Mapped[str] = mapped_column(String)  # image, video, audio, document

    # Size and format
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # for video/audio
    width: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # for images/video
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Deduplication
    content_hash: Mapped[str] = mapped_column(String, index=True)  # SHA256 hash

    # Organization
    tags: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON array
    source: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # generated, stock, uploaded
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )

    # AI/Semantic
    description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # AI-generated
    embedding: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # JSON CLIP embedding

    # Timestamps
    created_at: Mapped[str] = mapped_column(
        String, default=lambda: datetime.now().isoformat()
    )
    indexed_at: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # When embedding was created

    # Performance tracking for StyleGraph
    performance_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Engagement/retention score (0-1)


# --- Manager Class ---
class DatabaseManager:
    """
    Manages database interactions using SQLAlchemy ORM.

    Supports PostgreSQL (primary) and SQLite (fallback).
    Uses connection pooling for production workloads.
    """

    def __init__(self, db_url: str | None = None):
        # Determine database URL
        if db_url:
            self.db_url = db_url
        elif os.getenv("DATABASE_URL"):
            self.db_url = os.getenv("DATABASE_URL")
        else:
            # Use PostgreSQL from config (with fallback to SQLite for dev)
            self.db_url = config.DATABASE_URL

        # Handle Heroku-style postgres:// URLs
        if self.db_url and self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)

        # Determine if PostgreSQL or SQLite
        self.is_postgres = self.db_url.startswith("postgresql")

        # Create engine with appropriate settings
        if self.is_postgres:
            # PostgreSQL with connection pooling
            self.engine = create_engine(
                self.db_url,
                pool_size=config.DB_POOL_SIZE,
                max_overflow=config.DB_MAX_OVERFLOW,
                pool_timeout=config.DB_POOL_TIMEOUT,
                pool_pre_ping=True,  # Verify connections before use
                echo=config.DB_ECHO,
            )
            logger.info("🐘 Connected to PostgreSQL database")
        else:
            # SQLite (no connection pooling)
            self.engine = create_engine(
                self.db_url,
                echo=config.DB_ECHO,
            )
            logger.info("📁 Using SQLite database")

        self._init_db()

        # Create session factory once (instead of creating new Session each time)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _init_db(self):
        """Initialize all tables defined in Base models."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        """Yields a thread-safe database session."""
        session = self.SessionLocal()  # Use factory instead of Session(self.engine)
        try:
            yield session
            session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            session.rollback()
            logger.error(f"Database Integrity Error (duplicate/constraint): {e}")
            raise
        except sqlalchemy.exc.OperationalError as e:
            session.rollback()
            logger.error(f"Database Operational Error (connection/lock): {e}")
            raise
        except sqlalchemy.exc.SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database Error ({type(e).__name__}): {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected DB Session Error ({type(e).__name__}): {e}")
            raise
        finally:
            session.close()

    def add_video(self, filename: str, path: str, duration: float, style: str) -> int:
        with self.get_session() as session:
            video = Video(
                filename=filename, filepath=str(path), duration=duration, style=style
            )
            session.add(video)
            session.flush()  # Flush to get the ID
            return video.id

    def log_upload(self, video_id: int, platform: str, platform_id: str):
        with self.get_session() as session:
            post = PostedContent(
                video_id=video_id, platform=platform, platform_id=platform_id
            )
            session.add(post)

    def get_analytics(self) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql(select(PostedContent), conn)

    def get_all_posts(self) -> pd.DataFrame:
        query = (
            select(
                PostedContent.id,
                PostedContent.platform,
                PostedContent.posted_at,
                PostedContent.views,
                PostedContent.likes,
                Video.filename,
                Video.duration,
                Video.style,
            )
            .join(Video, PostedContent.video_id == Video.id)
            .order_by(PostedContent.posted_at.desc())
        )

        with self.engine.connect() as conn:
            return pd.read_sql(query, conn)

    def add_comment(self, comment_data: dict) -> int | None:
        with self.get_session() as session:
            stmt = select(Comment).where(
                Comment.platform_comment_id == comment_data.get("id")
            )
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                return None

            comment = Comment(
                platform=comment_data.get("platform", "youtube"),
                platform_comment_id=comment_data.get("id"),
                author=comment_data.get("author"),
                text=comment_data.get("text"),
                sentiment=comment_data.get("sentiment", "neutral"),
            )
            session.add(comment)
            session.flush()
            return comment.id

    def get_pending_comments(self) -> pd.DataFrame:
        stmt = select(Comment).where(Comment.status == "pending")
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def update_comment_reply(self, comment_id: int, reply: str):
        with self.get_session() as session:
            stmt = (
                update(Comment)
                .where(Comment.id == comment_id)
                .values(reply_draft=reply, status="drafted")
            )
            session.execute(stmt)

    # --- Project Management ---

    def create_project(
        self,
        name: str,
        description: str | None = None,
        platform: str | None = None,
        aspect_ratio: str = "16:9",
    ) -> int:
        """Create a new project."""
        with self.get_session() as session:
            project = Project(
                name=name,
                description=description,
                platform=platform,
                aspect_ratio=aspect_ratio,
            )
            session.add(project)
            session.flush()
            return project.id

    def get_project(self, project_id: int) -> dict | None:
        """Get a project by ID."""
        import json

        with self.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return None

            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "script": project.script,
                "caption": project.caption,
                "hashtags": project.hashtags,
                "audio_paths": json.loads(project.audio_paths)
                if project.audio_paths
                else [],
                "video_paths": json.loads(project.video_paths)
                if project.video_paths
                else [],
                "image_paths": json.loads(project.image_paths)
                if project.image_paths
                else [],
                "thumbnail_path": project.thumbnail_path,
                "output_path": project.output_path,
                "settings": json.loads(project.settings) if project.settings else {},
                "platform": project.platform,
                "aspect_ratio": project.aspect_ratio,
                "duration": project.duration,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
            }

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields."""
        import json

        with self.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False

            # Handle JSON fields
            for field in ["audio_paths", "video_paths", "image_paths", "settings"]:
                if field in kwargs and isinstance(kwargs[field], (list, dict)):
                    kwargs[field] = json.dumps(kwargs[field])

            # Update timestamp
            kwargs["updated_at"] = datetime.now().isoformat()

            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)

            return True

    def save_project_draft(
        self,
        project_id: int,
        script: str | None = None,
        audio_paths: list[str] | None = None,
        video_paths: list[str] | None = None,
        image_paths: list[str] | None = None,
        settings: dict | None = None,
    ) -> bool:
        """Save draft state of a project."""
        update_data = {"status": "draft"}

        if script is not None:
            update_data["script"] = script
        if audio_paths is not None:
            update_data["audio_paths"] = audio_paths
        if video_paths is not None:
            update_data["video_paths"] = video_paths
        if image_paths is not None:
            update_data["image_paths"] = image_paths
        if settings is not None:
            update_data["settings"] = settings

        return self.update_project(project_id, **update_data)

    def get_all_projects(self, status: str | None = None) -> pd.DataFrame:
        """Get all projects, optionally filtered by status."""
        if status:
            stmt = (
                select(Project)
                .where(Project.status == status)
                .order_by(Project.updated_at.desc())
            )
        else:
            stmt = select(Project).order_by(Project.updated_at.desc())

        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        with self.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                session.delete(project)
                return True
            return False

    def duplicate_project(self, project_id: int, new_name: str) -> int | None:
        """Duplicate a project with a new name."""
        import json

        original = self.get_project(project_id)
        if not original:
            return None

        with self.get_session() as session:
            new_project = Project(
                name=new_name,
                description=original.get("description"),
                script=original.get("script"),
                caption=original.get("caption"),
                hashtags=original.get("hashtags"),
                audio_paths=json.dumps(original.get("audio_paths", [])),
                video_paths=json.dumps(original.get("video_paths", [])),
                image_paths=json.dumps(original.get("image_paths", [])),
                settings=json.dumps(original.get("settings", {})),
                platform=original.get("platform"),
                aspect_ratio=original.get("aspect_ratio", "16:9"),
            )
            session.add(new_project)
            session.flush()
            return new_project.id
