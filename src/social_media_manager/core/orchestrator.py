import logging
from typing import Any

from ..ai.auditor import SalesAuditor

# AI Agents
from ..ai.brain import HybridBrain
from ..ai.campaign import CampaignArchitect
from ..ai.critic import CriticAgent
from ..ai.curator import SmartCurator
from ..ai.director import VideoDirector
from ..ai.dubber import ContentDubber
from ..ai.focus_group import DigitalFocusGroup
from ..ai.forecaster import TrendForecaster
from ..ai.hunter import StockHunter
from ..ai.memory import ContentMemory
from ..ai.newsroom import Newsroom
from ..ai.radar import TrendRadar
from ..ai.spy import CompetitorSpy
from ..ai.transcriber import WhisperTranscriber
from ..ai.visual_rag import VisualRAG

# Dependencies
from ..database import DatabaseManager
from ..models import ProcessedVideo
from ..platforms.uploader import PlatformUploader
from .avatar import AvatarEngine
from .client_manager import ClientManager
from .community import CommunityManager
from .monetizer import AffiliateScout
from .processor import VideoProcessor
from .reporter import ReportGenerator

logger = logging.getLogger(__name__)


class SocialMediaManager:
    """
    The Orchestrator. Manages the workflow between all agents and core systems.
    """

    def __init__(
        self,
        db: DatabaseManager | None = None,
        processor: VideoProcessor | None = None,
        uploader: PlatformUploader | None = None,
        brain: HybridBrain | None = None,
    ):
        # 1. Initialize Core Systems
        self.db = db if db else DatabaseManager()
        self.processor = processor if processor else VideoProcessor()
        self.uploader = uploader if uploader else PlatformUploader()

        self.client_manager = ClientManager()
        self.community = CommunityManager()
        self.monetizer = AffiliateScout()
        self.avatar_engine = AvatarEngine()

        # 2. Initialize AI Agents
        self.brain = brain if brain else self._init_agent(HybridBrain, "Brain")

        self.memory = self._init_agent(ContentMemory, "Memory")
        self.newsroom = self._init_agent(Newsroom, "Newsroom")
        self.critic = self._init_agent(CriticAgent, "Critic")
        self.forecaster = self._init_agent(
            TrendForecaster, "Forecaster", db_manager=self.db
        )
        self.radar = self._init_agent(TrendRadar, "Radar")
        self.spy = self._init_agent(CompetitorSpy, "Spy")
        self.director = self._init_agent(VideoDirector, "Director")
        self.auditor = self._init_agent(SalesAuditor, "Auditor")
        self.transcriber = self._init_agent(WhisperTranscriber, "Transcriber")
        self.curator = self._init_agent(SmartCurator, "Curator")
        self.dubber = self._init_agent(ContentDubber, "Dubber")
        self.reporter = self._init_agent(ReportGenerator, "Reporter")
        self.hunter = self._init_agent(StockHunter, "StockHunter")
        self.visual_rag = self._init_agent(VisualRAG, "VisualRAG")  # RAG-first B-roll
        self.campaign_architect = self._init_agent(
            CampaignArchitect, "CampaignArchitect"
        )
        self.focus_group = self._init_agent(
            DigitalFocusGroup, "FocusGroup"
        )  # <--- NEW AGENT

    def _init_agent(self, agent_class: Any, name: str, **kwargs) -> Any | None:
        try:
            return agent_class(**kwargs)
        except ImportError as e:
            logger.warning(f"⚠️ Agent '{name}' missing dependency: {e}")
            return None
        except TypeError as e:
            logger.warning(f"⚠️ Agent '{name}' init failed (bad args): {e}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Agent '{name}' failed to load ({type(e).__name__}): {e}")
            return None

    # --- MAIN VIDEO PIPELINE ---
    def process_video(
        self,
        raw_path: str,
        platforms: list[str] = ["youtube"],
        client_name: str | None = None,
        style_config: dict[str, Any] | None = None,
        options: dict[str, bool] | None = None,
    ) -> ProcessedVideo:
        logger.info(f"🚀 Processing {raw_path}")

        if not options:
            options = {
                "vertical_crop": False,
                "smart_cut": True,
                "polish": True,
                "captions": True,
                "visuals": True,
                "music": True,
                "monetization": True,
                "stock_fallback": True,
            }

        video_path = raw_path
        if options.get("smart_cut"):
            video_path = self.processor.smart_cut(video_path)
        if options.get("vertical_crop"):
            video_path = self.processor.convert_to_vertical(video_path)
        if options.get("polish"):
            video_path = self.processor.apply_polish(video_path)

        srt_path = None
        if self.transcriber:
            srt_path = self.transcriber.generate_srt(video_path)

        if srt_path and self.brain:
            if options.get("visuals"):
                plan = self._generate_visual_plan(
                    srt_path, options.get("stock_fallback", True)
                )
                video_path = self.processor.overlay_visuals(video_path, plan)
            if options.get("captions"):
                video_path = self.processor.burn_captions(
                    video_path, srt_path, style_config
                )

        if options.get("music"):
            video_path = self.processor.add_background_music(video_path)

        info = self.processor.get_info(video_path)
        caption = "Auto-generated"

        if self.brain:
            context = (
                self.client_manager.get_client_context(client_name)
                if client_name
                else "General"
            )
            caption = self.brain.generate_client_content(
                context, f"Video: {info['filename']}", "Social"
            )

            if self.memory:
                self.memory.save_post(info["filename"], caption, platforms[0])

        video_id = self.db.add_video(
            info["filename"], video_path, info["duration"], client_name or "General"
        )

        result = ProcessedVideo(
            id=video_id,
            path=str(video_path),
            caption=caption,
            srt_path=srt_path,
            platform=platforms[0] if platforms else "youtube",
            style=client_name or "General",
        )
        for p in platforms:
            self.uploader.upload(p, result.to_dict())

        return result

    def _generate_visual_plan(
        self, srt_path: str, use_stock: bool = True
    ) -> list[dict[str, Any]]:
        plan = []
        try:
            with open(srt_path, "r") as f:
                content = f.read()
            import re

            matches = re.findall(
                r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)",
                content,
                re.DOTALL,
            )

            def to_sec(t):
                h, m, s = t.split(":")
                s, ms = s.split(",")
                return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

            last_end = 0
            for _, s, e, text in matches:
                start = to_sec(s)
                if start - last_end < 10:
                    continue

                # Ask Brain for visual keywords
                if self.brain:
                    q = self.brain.extract_visual_keywords(text.replace("\n", " "))
                    path = None
                    clip_duration = 4.0  # Default clip duration

                    # 0. VisualRAG (Semantic B-roll Search) - FIRST PRIORITY
                    if self.visual_rag and not path:
                        try:
                            rag_result = self.visual_rag.find_best_clip(
                                description=q,
                                duration=clip_duration,
                            )
                            # Only use if score exceeds threshold (0.75)
                            if rag_result and rag_result.get("score", 0) >= 0.75:
                                path = rag_result.get("path")
                                clip_duration = rag_result.get("duration", 4.0)
                                logger.info(
                                    f"✅ RAG match (score={rag_result.get('score'):.2f}): {path}"
                                )
                        except Exception as e:
                            logger.warning(f"⚠️ VisualRAG search failed: {e}")

                    # 1. Curator (Local) - Fallback #1
                    if not path and self.curator:
                        path = self.curator.find_best_match(q)

                    # 2. Director (AI Gen) - Fallback #2
                    if not path and self.director:
                        # Only gen image if curator failed
                        path = self.director.generate_image(f"Cinematic {q}")

                    # 3. Hunter (Stock) - Fallback #3
                    if not path and self.hunter and use_stock:
                        path = self.hunter.hunt(q)

                    if path:
                        plan.append(
                            {"start": start, "end": start + clip_duration, "path": path}
                        )
                        last_end = start + clip_duration
        except FileNotFoundError as e:
            logger.error(f"Visual Plan Error: File not found: {e}")
        except OSError as e:
            logger.error(f"Visual Plan Error (I/O): {e}")
        except ValueError as e:
            logger.error(f"Visual Plan Error (bad value): {e}")
        except Exception as e:
            logger.error(f"Visual Plan Error ({type(e).__name__}): {e}")

        return plan

    # --- NEW CAPABILITIES ---

    def create_global_content(self, topic: str, languages: list[str]) -> dict[str, str]:
        """Generates dubbed content in multiple languages."""
        results = {}
        if not self.brain or not self.dubber:
            logger.error("Brain or Dubber missing.")
            return results

        # 1. Generate Script
        script = self.brain.think(
            f"Write a 30-second educational script about: {topic}"
        )

        # 2. Loop languages
        for lang in languages:
            # Brain translates first
            translated_script = self.brain.think(f"Translate this to {lang}: {script}")

            # Dubber speaks it
            _, audio_path = self.dubber.dub_content(translated_script, lang)

            if audio_path:
                # Avatar animates it (Optional)
                video_path = self.avatar_engine.generate_talking_head(audio_path)
                results[lang] = video_path if video_path else audio_path

        return results

    def process_breaking_news(self) -> dict[str, Any] | None:
        """Scans news, writes script, and generates AI news anchor video."""
        if not self.newsroom or not self.brain:
            return None

        # 1. Check for news
        news = self.newsroom.check_for_breaking_news()
        if not news:
            return None

        # 2. Write Script
        script = self.brain.think(
            f"Write a 45-second Breaking News script about: {news['topic']}. Hook: {news['hook']}."
        )

        # 3. Create Video (Avatar)
        if self.dubber and self.avatar_engine:
            _, audio_path = self.dubber.dub_content(script, "English")
            if audio_path:
                video_path = self.avatar_engine.generate_talking_head(audio_path)
                if video_path:
                    # Save to DB
                    self.db.add_video(f"News_{news['topic']}", video_path, 45.0, "News")
                    return {
                        "topic": news["topic"],
                        "video_path": video_path,
                        "script": script,
                    }

        return {
            "topic": news["topic"],
            "script": script,
            "error": "Could not render video",
        }
