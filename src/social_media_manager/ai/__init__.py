from .ab_optimizer import ABOptimizer, ABTest, Variant, generate_ab_test
from .auditor import SalesAuditor
from .avatar import AvatarEngine, create_news_anchor, create_talking_head
from .background_remover import BackgroundRemover, remove_bg
from .brain import HybridBrain
from .browser_spy import (
    BrowserSpy,
    BrowserSpySync,
    CompetitorProfile,
    spy_on_competitor,
)
from .campaign import CampaignArchitect
from .composer import MusicComposer, compose_for_style, compose_music
from .critic import CriticAgent
from .curator import SmartCurator
from .director import VideoDirector
from .dubber import ContentDubber
from .focus_group import DigitalFocusGroup
from .forecaster import TrendForecaster
from .hunter import StockHunter
from .memory import ContentMemory
from .newsroom import Newsroom
from .producer import VideoProducer, produce_video
from .radar import TrendRadar
from .repurposer import ContentRepurposer
from .rl_scheduler import RLScheduler
from .seo_agent import (
    SEOAgent,
    SEOAnalysis,
    get_hashtags,
    optimize_caption,
    research_keyword,
)
from .spy import CompetitorSpy
from .style_tuner import StyleProfile, StyleTuner, generate_in_style, train_client_style
from .transcriber import WhisperTranscriber
from .upscaler import (
    FaceRestorer,
    ImageUpscaler,
    enhance_image,
    restore_faces,
    upscale_image,
)
from .visual_rag import FrameMatch, VisualRAG, index_footage, search_footage

# --- FIXED SECTION ---
from .voice_cloner import (
    VoiceCloner,
    clone_voice,
)

# ---------------------
from .watchdog import CompetitorWatchdog
from .world_sim import GeminiWorldSim
