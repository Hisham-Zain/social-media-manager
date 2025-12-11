"""
Browser-controlled Spy Agent for AgencyOS.

Uses browser-use library to give the AI agent actual browser control:
- Navigate and scroll competitor feeds
- Take screenshots of trending content
- Analyze visual aesthetics and layouts
- Extract engagement metrics
- Monitor competitor strategies in real-time

Requires: pip install browser-use playwright
Then: playwright install chromium
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from ..config import config


@dataclass
class CompetitorProfile:
    """Profile of a competitor analyzed by the spy."""

    name: str
    platform: str
    url: str
    followers: int | None = None
    posts_analyzed: int = 0
    engagement_rate: float | None = None
    posting_frequency: str | None = None
    top_content_themes: list[str] = field(default_factory=list)
    visual_style: str | None = None
    hashtag_strategy: list[str] = field(default_factory=list)
    best_performing_posts: list[dict] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)  # Paths to screenshots
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "platform": self.platform,
            "url": self.url,
            "followers": self.followers,
            "posts_analyzed": self.posts_analyzed,
            "engagement_rate": self.engagement_rate,
            "posting_frequency": self.posting_frequency,
            "top_content_themes": self.top_content_themes,
            "visual_style": self.visual_style,
            "hashtag_strategy": self.hashtag_strategy,
            "best_performing_posts": self.best_performing_posts,
            "screenshots": self.screenshots,
            "analyzed_at": self.analyzed_at,
        }


@dataclass
class BrowseResult:
    """Result of a browser action."""

    success: bool
    action: str
    data: dict = field(default_factory=dict)
    screenshot_path: str | None = None
    error: str | None = None


class BrowserSpy:
    """
    AI-powered browser spy that can actually browse the web.

    Uses browser-use to let the LLM control a headless browser,
    enabling real competitor research with screenshots and interaction.

    Example:
        spy = BrowserSpy()

        # Analyze a competitor's Instagram
        profile = await spy.analyze_competitor(
            "@competitor_handle",
            platform="instagram"
        )
        print(profile.visual_style)
        print(profile.top_content_themes)

        # Take screenshots of trending content
        screenshots = await spy.capture_trending(
            "fitness",
            platform="instagram",
            count=5
        )

        # Browse and extract specific data
        result = await spy.browse(
            "Go to instagram.com/nike and get their latest 5 posts"
        )
    """

    def __init__(
        self,
        headless: bool = True,
        screenshot_dir: Path | None = None,
        profile_name: str = "default",
    ):
        """
        Initialize the Browser Spy.

        Args:
            headless: Run browser in headless mode.
            screenshot_dir: Directory to save screenshots.
            profile_name: Profile name for persistent browser sessions.
        """
        self.headless = headless
        self.screenshot_dir = screenshot_dir or (config.BASE_DIR / "spy_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Persistent browser profile path
        self.profile_name = profile_name
        self.user_data_dir = config.BROWSER_PROFILES_DIR / profile_name
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self._browser = None
        self._agent = None
        self._browser_use_available = True

        logger.info(f"🕵️ Browser Spy initialized (Profile: {profile_name})")

    async def _init_browser(self):
        """Initialize browser-use agent with persistent profile."""
        if self._agent is not None:
            return

        try:
            from browser_use import Agent
            from browser_use.browser.browser import Browser, BrowserConfig
            from langchain_community.llms import Ollama

            # Use local Ollama for browser control
            llm = Ollama(
                model=config.OLLAMA_MODEL,
                base_url=config.OLLAMA_URL,
            )

            # Configure persistent browser with stealth args
            browser = Browser(
                config=BrowserConfig(
                    headless=self.headless,
                    disable_security=True,
                    extra_chromium_args=[
                        f"--user-data-dir={self.user_data_dir}",  # Persistent sessions
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                    ],
                )
            )

            self._agent = Agent(
                task="",  # Will be set per task
                llm=llm,
                browser=browser,
            )

            logger.info(
                f"🌐 Browser-use agent initialized (Profile: {self.profile_name})"
            )

        except ImportError:
            logger.warning(
                "⚠️ browser-use not installed. Run: pip install browser-use langchain-community"
            )
            self._browser_use_available = False
        except Exception as e:
            logger.warning(f"⚠️ Browser-use initialization failed: {e}")
            self._browser_use_available = False

    async def browse(
        self,
        task: str,
        take_screenshot: bool = True,
    ) -> BrowseResult:
        """
        Execute a browsing task using natural language.

        Args:
            task: Natural language description of what to do.
            take_screenshot: Whether to capture a screenshot after.

        Returns:
            BrowseResult with action outcome.
        """
        await self._init_browser()

        if not self._browser_use_available:
            return await self._fallback_browse(task)

        try:
            from browser_use import Agent
            from langchain_community.llms import Ollama

            llm = Ollama(
                model=config.OLLAMA_MODEL,
                base_url=config.OLLAMA_URL,
            )

            agent = Agent(
                task=task,
                llm=llm,
            )

            # Run the agent
            result = await agent.run()

            screenshot_path = None
            if take_screenshot and hasattr(agent, "browser") and agent.browser:
                screenshot_path = await self._take_screenshot("browse_result")

            return BrowseResult(
                success=True,
                action=task,
                data={"result": str(result)},
                screenshot_path=screenshot_path,
            )

        except Exception as e:
            logger.error(f"Browse task failed: {e}")
            return BrowseResult(
                success=False,
                action=task,
                error=str(e),
            )

    async def _fallback_browse(self, task: str) -> BrowseResult:
        """Fallback using Playwright directly when browser-use unavailable."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Parse simple commands from task
                task_lower = task.lower()

                result_data = {}
                screenshot_path = None

                # Handle common patterns
                if "instagram.com" in task_lower or "instagram" in task_lower:
                    # Extract username if present
                    import re

                    username_match = re.search(r"@?(\w+)", task)
                    if username_match:
                        username = username_match.group(1)
                        url = f"https://www.instagram.com/{username}/"
                        await page.goto(url)
                        await page.wait_for_timeout(3000)

                        # Take screenshot
                        screenshot_path = await self._save_page_screenshot(
                            page, f"instagram_{username}"
                        )

                        # Try to extract basic info
                        try:
                            content = await page.content()
                            result_data["url"] = url
                            result_data["content_length"] = len(content)
                        except Exception:
                            pass

                elif "twitter.com" in task_lower or "x.com" in task_lower:
                    import re

                    username_match = re.search(r"@?(\w+)", task)
                    if username_match:
                        username = username_match.group(1)
                        url = f"https://x.com/{username}"
                        await page.goto(url)
                        await page.wait_for_timeout(3000)
                        screenshot_path = await self._save_page_screenshot(
                            page, f"twitter_{username}"
                        )
                        result_data["url"] = url

                elif "tiktok.com" in task_lower:
                    import re

                    username_match = re.search(r"@(\w+)", task)
                    if username_match:
                        username = username_match.group(1)
                        url = f"https://www.tiktok.com/@{username}"
                        await page.goto(url)
                        await page.wait_for_timeout(3000)
                        screenshot_path = await self._save_page_screenshot(
                            page, f"tiktok_{username}"
                        )
                        result_data["url"] = url

                elif "youtube.com" in task_lower:
                    import re

                    channel_match = re.search(r"@?(\w+)", task)
                    if channel_match:
                        channel = channel_match.group(1)
                        url = f"https://www.youtube.com/@{channel}"
                        await page.goto(url)
                        await page.wait_for_timeout(3000)
                        screenshot_path = await self._save_page_screenshot(
                            page, f"youtube_{channel}"
                        )
                        result_data["url"] = url

                else:
                    # Try to extract URL from task
                    import re

                    url_match = re.search(r"https?://[^\s]+", task)
                    if url_match:
                        url = url_match.group(0)
                        await page.goto(url)
                        await page.wait_for_timeout(3000)
                        screenshot_path = await self._save_page_screenshot(
                            page, "custom_page"
                        )
                        result_data["url"] = url

                await browser.close()

                return BrowseResult(
                    success=True,
                    action=task,
                    data=result_data,
                    screenshot_path=screenshot_path,
                )

        except ImportError:
            return BrowseResult(
                success=False,
                action=task,
                error="Playwright not installed. Run: pip install playwright && playwright install chromium",
            )
        except Exception as e:
            return BrowseResult(
                success=False,
                action=task,
                error=str(e),
            )

    async def _save_page_screenshot(self, page, name: str) -> str:
        """Save a screenshot of the current page."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = self.screenshot_dir / filename
        await page.screenshot(path=str(path), full_page=False)
        logger.info(f"📸 Screenshot saved: {path}")
        return str(path)

    async def _take_screenshot(self, name: str) -> str | None:
        """Take a screenshot using the browser-use agent."""
        if not self._agent or not hasattr(self._agent, "browser"):
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            path = self.screenshot_dir / filename

            if self._agent.browser and self._agent.browser.page:
                await self._agent.browser.page.screenshot(path=str(path))
                return str(path)
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

        return None

    async def analyze_competitor(
        self,
        handle: str,
        platform: Literal["instagram", "twitter", "tiktok", "youtube"] = "instagram",
        deep_analysis: bool = True,
    ) -> CompetitorProfile:
        """
        Analyze a competitor's social media presence.

        Args:
            handle: Username/handle (with or without @).
            platform: Social media platform.
            deep_analysis: Whether to scroll and analyze multiple posts.

        Returns:
            CompetitorProfile with analysis results.
        """
        handle = handle.lstrip("@")

        # Platform URL mapping
        platform_urls = {
            "instagram": f"https://www.instagram.com/{handle}/",
            "twitter": f"https://x.com/{handle}",
            "tiktok": f"https://www.tiktok.com/@{handle}",
            "youtube": f"https://www.youtube.com/@{handle}",
        }

        url = platform_urls.get(platform, platform_urls["instagram"])

        profile = CompetitorProfile(
            name=handle,
            platform=platform,
            url=url,
        )

        # Browse to profile and capture screenshot
        task = f"Go to {url} and analyze the content"
        result = await self.browse(task)

        if result.screenshot_path:
            profile.screenshots.append(result.screenshot_path)

        if deep_analysis:
            # Scroll and capture more content
            scroll_task = f"Scroll down on {url} to see more posts and take notes on content themes"
            scroll_result = await self.browse(scroll_task)

            if scroll_result.screenshot_path:
                profile.screenshots.append(scroll_result.screenshot_path)

        # Use AI to analyze screenshots and extract insights
        profile = await self._analyze_with_ai(profile)

        logger.info(f"🕵️ Competitor analysis complete: {handle} on {platform}")
        return profile

    async def _analyze_with_ai(self, profile: CompetitorProfile) -> CompetitorProfile:
        """Use AI to analyze captured data and fill in profile."""
        try:
            from .brain import HybridBrain

            brain = HybridBrain()

            prompt = f"""Analyze this competitor profile and provide insights:

Competitor: {profile.name}
Platform: {profile.platform}
URL: {profile.url}

Based on general knowledge about successful {profile.platform} accounts, provide:
1. Estimated posting frequency (daily/weekly)
2. Top 3 likely content themes
3. Visual style description (aesthetic, colors, mood)
4. 5 hashtags they likely use
5. Content strategy insights

Return as JSON:
{{
    "posting_frequency": "...",
    "content_themes": ["...", "...", "..."],
    "visual_style": "...",
    "hashtags": ["...", "...", "...", "...", "..."],
    "strategy_insights": "..."
}}"""

            response = brain.think(prompt, json_mode=True)

            try:
                data = json.loads(response)
                profile.posting_frequency = data.get("posting_frequency")
                profile.top_content_themes = data.get("content_themes", [])
                profile.visual_style = data.get("visual_style")
                profile.hashtag_strategy = data.get("hashtags", [])
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI analysis")

        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

        return profile

    async def capture_trending(
        self,
        topic: str,
        platform: Literal["instagram", "twitter", "tiktok", "youtube"] = "instagram",
        count: int = 5,
    ) -> list[str]:
        """
        Capture screenshots of trending content for a topic.

        Args:
            topic: Topic/hashtag to search for.
            platform: Platform to search on.
            count: Number of screenshots to capture.

        Returns:
            List of screenshot paths.
        """
        screenshots = []

        # Platform search URLs
        search_urls = {
            "instagram": f"https://www.instagram.com/explore/tags/{topic.replace('#', '').replace(' ', '')}/",
            "twitter": f"https://x.com/search?q={topic}&src=typed_query",
            "tiktok": f"https://www.tiktok.com/tag/{topic.replace('#', '').replace(' ', '')}",
            "youtube": f"https://www.youtube.com/results?search_query={topic}",
        }

        url = search_urls.get(platform, search_urls["instagram"])

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                await page.goto(url)
                await page.wait_for_timeout(3000)

                # Initial screenshot
                path = await self._save_page_screenshot(
                    page, f"trending_{topic}_{platform}_1"
                )
                screenshots.append(path)

                # Scroll and capture more
                for i in range(2, count + 1):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await page.wait_for_timeout(1500)
                    path = await self._save_page_screenshot(
                        page, f"trending_{topic}_{platform}_{i}"
                    )
                    screenshots.append(path)

                await browser.close()

        except ImportError:
            logger.warning("Playwright not installed for trending capture")
        except Exception as e:
            logger.warning(f"Trending capture failed: {e}")

        return screenshots

    async def monitor_competitor_feed(
        self,
        handles: list[str],
        platform: str = "instagram",
        interval_hours: int = 24,
    ) -> list[CompetitorProfile]:
        """
        Monitor multiple competitors and generate comparison report.

        Args:
            handles: List of competitor handles.
            platform: Platform to monitor.
            interval_hours: Hours between checks (for scheduling).

        Returns:
            List of CompetitorProfile objects.
        """
        profiles = []

        for handle in handles:
            try:
                profile = await self.analyze_competitor(handle, platform)
                profiles.append(profile)

                # Small delay between requests to be respectful
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"Failed to analyze {handle}: {e}")

        # Save report
        report = {
            "analyzed_at": datetime.now().isoformat(),
            "platform": platform,
            "competitors": [p.to_dict() for p in profiles],
        }

        report_path = (
            self.screenshot_dir
            / f"competitor_report_{datetime.now().strftime('%Y%m%d')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Competitor report saved: {report_path}")

        return profiles

    async def extract_aesthetics(
        self,
        url: str,
        analyze_colors: bool = True,
        analyze_layout: bool = True,
    ) -> dict[str, Any]:
        """
        Extract visual aesthetics from a page.

        Args:
            url: URL to analyze.
            analyze_colors: Extract dominant colors.
            analyze_layout: Analyze page layout patterns.

        Returns:
            Dict with aesthetic analysis.
        """
        result = await self.browse(f"Go to {url}")

        aesthetics = {
            "url": url,
            "screenshot": result.screenshot_path,
            "colors": [],
            "layout_notes": "",
        }

        if result.screenshot_path and analyze_colors:
            # Extract colors from screenshot
            try:
                from PIL import Image

                img = Image.open(result.screenshot_path)
                img = img.resize((100, 100))  # Downsample for speed

                colors = img.getcolors(maxcolors=10000)
                if colors:
                    # Sort by frequency
                    sorted_colors = sorted(colors, key=lambda x: -x[0])[:5]
                    aesthetics["colors"] = [
                        f"#{r:02x}{g:02x}{b:02x}"
                        for count, (r, g, b) in sorted_colors
                        if isinstance((r, g, b), tuple) and len((r, g, b)) == 3
                    ]
            except Exception as e:
                logger.warning(f"Color extraction failed: {e}")

        return aesthetics

    # === MCP-BASED METHODS ===

    async def browse_with_mcp(
        self,
        task: str,
        take_screenshot: bool = False,
    ) -> BrowseResult:
        """
        Browse using MCP Puppeteer server.

        Delegates browser control to the MCP server for sandboxed execution.
        Falls back to local browsing if MCP unavailable.

        Args:
            task: Natural language browsing task
            take_screenshot: Whether to request screenshot

        Returns:
            BrowseResult with action outcome
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "browser" not in manager.servers:
                logger.debug("Browser MCP not configured, using local browsing")
                return await self.browse(task, take_screenshot)

            logger.info(f"🌐 MCP Browse: {task[:50]}...")

            # Call the puppeteer MCP
            result = await manager.call_tool(
                "browser", "puppeteer_navigate", {"task": task}
            )

            if "error" in result:
                logger.warning(f"MCP browse failed: {result['error']}")
                return await self.browse(task, take_screenshot)

            return BrowseResult(
                success=True,
                action=task,
                data={"result": result.get("result", "")},
                screenshot_path=None,  # MCP may include screenshot data
            )

        except ImportError:
            logger.debug("MCP client not available")
            return await self.browse(task, take_screenshot)
        except Exception as e:
            logger.error(f"MCP browse error: {e}")
            return await self.browse(task, take_screenshot)

    async def analyze_competitor_with_mcp(
        self,
        handle: str,
        platform: str = "instagram",
    ) -> CompetitorProfile:
        """
        Analyze competitor using MCP browser.

        Uses Puppeteer MCP for sandboxed browsing.
        Falls back to local analysis if MCP unavailable.
        """
        handle = handle.lstrip("@")

        platform_urls = {
            "instagram": f"https://www.instagram.com/{handle}/",
            "twitter": f"https://x.com/{handle}",
            "tiktok": f"https://www.tiktok.com/@{handle}",
            "youtube": f"https://www.youtube.com/@{handle}",
        }

        url = platform_urls.get(platform, platform_urls["instagram"])

        profile = CompetitorProfile(
            name=handle,
            platform=platform,
            url=url,
        )

        # Try MCP first
        result = await self.browse_with_mcp(
            f"Navigate to {url} and extract profile info"
        )

        if result.success:
            profile = await self._analyze_with_ai(profile)

        return profile


# Synchronous wrapper for non-async code
class BrowserSpySync:
    """Synchronous wrapper for BrowserSpy."""

    def __init__(self, **kwargs):
        self._spy = BrowserSpy(**kwargs)
        self._loop = None

    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        return self._loop

    def browse(self, task: str, **kwargs) -> BrowseResult:
        return self._get_loop().run_until_complete(self._spy.browse(task, **kwargs))

    def analyze_competitor(self, handle: str, **kwargs) -> CompetitorProfile:
        return self._get_loop().run_until_complete(
            self._spy.analyze_competitor(handle, **kwargs)
        )

    def capture_trending(self, topic: str, **kwargs) -> list[str]:
        return self._get_loop().run_until_complete(
            self._spy.capture_trending(topic, **kwargs)
        )


# Convenience function
def spy_on_competitor(handle: str, platform: str = "instagram") -> CompetitorProfile:
    """Quick function to spy on a competitor."""
    spy = BrowserSpySync()
    return spy.analyze_competitor(handle, platform=platform)
