"""
SEO Specialist Agent for AgencyOS.

Uses real data to find trending keywords and optimize content:
- Pytrends: Google Trends data without an API key
- Datamuse: Synonyms, related words, and rhymes (free API)

Features:
- Keyword trend analysis
- Related search queries
- Rising topics detection
- Caption optimization with trending terms
- Hashtag suggestions based on real search data
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from loguru import logger


@dataclass
class KeywordData:
    """Keyword analysis results."""

    keyword: str
    interest: int  # 0-100 relative interest
    trend: Literal["rising", "stable", "declining"]
    related_queries: list[str] = field(default_factory=list)
    rising_queries: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "interest": self.interest,
            "trend": self.trend,
            "related_queries": self.related_queries,
            "rising_queries": self.rising_queries,
            "synonyms": self.synonyms,
        }


@dataclass
class SEOAnalysis:
    """Full SEO analysis of content."""

    original_text: str
    optimized_text: str
    keywords_found: list[KeywordData]
    suggested_hashtags: list[str]
    score: float  # 0-100 SEO score
    improvements: list[str]


class SEOAgent:
    """
    SEO Specialist that uses real data to optimize content.

    Example:
        seo = SEOAgent()

        # Analyze keywords
        trends = seo.get_trends(["AI", "Machine Learning", "ChatGPT"])

        # Optimize a caption
        result = seo.optimize_caption(
            "Check out our new AI tool!",
            niche="technology"
        )
        print(result.optimized_text)
        print(result.suggested_hashtags)

        # Get hashtag suggestions
        hashtags = seo.suggest_hashtags("fitness workout routine")
    """

    def __init__(self):
        """Initialize SEO Agent."""
        self._pytrends = None
        self._trends_available = True

        logger.info("🔍 SEO Agent initialized")

    @property
    def pytrends(self):
        """Lazy load pytrends."""
        if self._pytrends is None and self._trends_available:
            try:
                from pytrends.request import TrendReq

                self._pytrends = TrendReq(hl="en-US", tz=360)
                logger.info("📈 Pytrends connected to Google Trends")
            except ImportError:
                logger.warning("⚠️ Pytrends not installed. Run: pip install pytrends")
                self._trends_available = False
            except Exception as e:
                logger.warning(f"⚠️ Pytrends connection failed: {e}")
                self._trends_available = False
        return self._pytrends

    def get_trends(
        self,
        keywords: list[str],
        timeframe: str = "today 3-m",
        geo: str = "",
    ) -> list[KeywordData]:
        """
        Get Google Trends data for keywords.

        Args:
            keywords: List of keywords (max 5).
            timeframe: Time range (default: 3 months).
                Options: "now 1-H", "now 4-H", "now 1-d", "now 7-d",
                        "today 1-m", "today 3-m", "today 12-m", "today 5-y"
            geo: Geographic region (e.g., "US", "GB", "").

        Returns:
            List of KeywordData with trends info.
        """
        results = []

        # Limit to 5 keywords (Google Trends limit)
        keywords = keywords[:5]

        if self.pytrends is None:
            # Fallback: return basic data without trends
            for kw in keywords:
                results.append(
                    KeywordData(
                        keyword=kw,
                        interest=50,
                        trend="stable",
                        synonyms=self._get_synonyms(kw),
                    )
                )
            return results

        try:
            # Build payload
            self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)

            # Get interest over time
            interest_df = self.pytrends.interest_over_time()

            # Get related queries
            related = self.pytrends.related_queries()

            for kw in keywords:
                # Calculate average interest
                if not interest_df.empty and kw in interest_df.columns:
                    interest = int(interest_df[kw].mean())

                    # Determine trend direction
                    recent = interest_df[kw].tail(7).mean()
                    older = interest_df[kw].head(7).mean()

                    if recent > older * 1.1:
                        trend = "rising"
                    elif recent < older * 0.9:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    interest = 50
                    trend = "stable"

                # Get related/rising queries
                related_queries = []
                rising_queries = []

                if kw in related and related[kw] is not None:
                    top = related[kw].get("top")
                    rising = related[kw].get("rising")

                    if top is not None and not top.empty:
                        related_queries = top["query"].tolist()[:10]

                    if rising is not None and not rising.empty:
                        rising_queries = rising["query"].tolist()[:10]

                results.append(
                    KeywordData(
                        keyword=kw,
                        interest=interest,
                        trend=trend,
                        related_queries=related_queries,
                        rising_queries=rising_queries,
                        synonyms=self._get_synonyms(kw),
                    )
                )

        except Exception as e:
            logger.warning(f"Trends lookup failed: {e}")
            # Fallback
            for kw in keywords:
                results.append(
                    KeywordData(
                        keyword=kw,
                        interest=50,
                        trend="stable",
                        synonyms=self._get_synonyms(kw),
                    )
                )

        return results

    def get_rising_topics(
        self,
        category: str = "",
        geo: str = "US",
    ) -> list[dict]:
        """
        Get currently rising topics from Google Trends.

        Args:
            category: Category to filter (e.g., "technology", "health").
            geo: Geographic region.

        Returns:
            List of trending topics with title and traffic.
        """
        if self.pytrends is None:
            return []

        try:
            trending = self.pytrends.trending_searches(
                pn=geo.lower() if geo else "united_states"
            )
            return [
                {"topic": topic, "trend": "rising"}
                for topic in trending[0].tolist()[:20]
            ]
        except Exception as e:
            logger.warning(f"Rising topics lookup failed: {e}")
            return []

    def _get_synonyms(self, word: str, max_results: int = 10) -> list[str]:
        """Get synonyms from Datamuse API."""
        import requests

        try:
            # Get synonyms (means like)
            response = requests.get(
                "https://api.datamuse.com/words",
                params={"ml": word, "max": max_results},
                timeout=5,
            )

            if response.status_code == 200:
                return [item["word"] for item in response.json()]
            return []

        except Exception:
            return []

    def get_related_words(
        self,
        word: str,
        relation: Literal[
            "synonyms", "antonyms", "rhymes", "sounds_like", "adjectives", "nouns"
        ] = "synonyms",
        max_results: int = 10,
    ) -> list[str]:
        """
        Get related words from Datamuse API.

        Args:
            word: The word to find relations for.
            relation: Type of relation.
            max_results: Maximum number of results.

        Returns:
            List of related words.
        """
        import requests

        # Map relation types to Datamuse parameters
        param_map = {
            "synonyms": "ml",  # Means like
            "antonyms": "rel_ant",  # Antonyms
            "rhymes": "rel_rhy",  # Rhymes
            "sounds_like": "sl",  # Sounds like
            "adjectives": "rel_jjb",  # Adjectives describing noun
            "nouns": "rel_jja",  # Nouns described by adjective
        }

        param = param_map.get(relation, "ml")

        try:
            response = requests.get(
                "https://api.datamuse.com/words",
                params={param: word, "max": max_results},
                timeout=5,
            )

            if response.status_code == 200:
                return [item["word"] for item in response.json()]
            return []

        except Exception as e:
            logger.warning(f"Datamuse lookup failed: {e}")
            return []

    def suggest_hashtags(
        self,
        text: str,
        platform: Literal["instagram", "twitter", "linkedin", "tiktok"] = "instagram",
        max_hashtags: int = 15,
    ) -> list[str]:
        """
        Suggest hashtags based on content and trends.

        Args:
            text: Content text to analyze.
            platform: Target platform.
            max_hashtags: Maximum number of hashtags.

        Returns:
            List of suggested hashtags (without #).
        """
        import requests

        # Extract key phrases from text
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Remove common stop words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "has",
            "have",
            "been",
            "were",
            "being",
            "this",
            "that",
            "with",
            "they",
            "from",
            "what",
            "which",
            "when",
            "will",
            "more",
            "some",
            "into",
            "your",
            "just",
            "about",
            "would",
            "there",
        }

        keywords = [w for w in words if w not in stop_words]

        # Get unique keywords by frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        top_keywords = sorted(word_freq.keys(), key=lambda x: -word_freq[x])[:5]

        hashtags = set()

        # Add top keywords as hashtags
        for kw in top_keywords:
            hashtags.add(kw)

        # Get related words from Datamuse
        for kw in top_keywords[:3]:
            try:
                response = requests.get(
                    "https://api.datamuse.com/words",
                    params={"ml": kw, "max": 5},
                    timeout=3,
                )
                if response.status_code == 200:
                    for item in response.json():
                        word = item["word"].replace(" ", "")
                        if len(word) <= 20:  # Reasonable hashtag length
                            hashtags.add(word)
            except Exception:
                pass

        # Get trending related queries if available
        if self.pytrends:
            try:
                trends = self.get_trends(top_keywords[:3])
                for trend in trends:
                    for query in trend.related_queries[:3]:
                        # Convert query to hashtag format
                        tag = query.replace(" ", "").lower()
                        if len(tag) <= 25:
                            hashtags.add(tag)
            except Exception:
                pass

        # Platform-specific adjustments
        platform_limits = {
            "instagram": 30,
            "twitter": 3,
            "linkedin": 5,
            "tiktok": 10,
        }

        limit = min(max_hashtags, platform_limits.get(platform, 15))

        # Return sorted by length (shorter first, more readable)
        return sorted(list(hashtags), key=len)[:limit]

    def optimize_caption(
        self,
        text: str,
        niche: str = "",
        platform: Literal["instagram", "twitter", "linkedin", "tiktok"] = "instagram",
        include_hashtags: bool = True,
    ) -> SEOAnalysis:
        """
        Optimize a caption with SEO best practices.

        Args:
            text: Original caption text.
            niche: Content niche (e.g., "fitness", "tech", "food").
            platform: Target platform.
            include_hashtags: Whether to add hashtags.

        Returns:
            SEOAnalysis with optimized text and suggestions.
        """
        improvements = []
        optimized = text
        score = 50  # Base score

        # Extract current keywords
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Analyze current keywords
        keywords_data = []
        if words:
            # Get top 5 unique words
            unique_words = list(dict.fromkeys(words))[:5]
            keywords_data = self.get_trends(unique_words)

        # Check for declining keywords
        declining = [kd for kd in keywords_data if kd.trend == "declining"]
        if declining:
            improvements.append(
                f"⚠️ Keywords declining in search: {', '.join(kd.keyword for kd in declining)}"
            )
            score -= 10

            # Suggest rising alternatives
            for kd in declining:
                if kd.rising_queries:
                    improvements.append(
                        f"💡 Consider using: {', '.join(kd.rising_queries[:3])}"
                    )

        # Check for rising keywords
        rising = [kd for kd in keywords_data if kd.trend == "rising"]
        if rising:
            score += 15
            improvements.append(
                f"✅ Trending keywords found: {', '.join(kd.keyword for kd in rising)}"
            )

        # Caption length optimization
        char_count = len(text)
        platform_optimal = {
            "instagram": (138, 150),
            "twitter": (71, 100),
            "linkedin": (100, 140),
            "tiktok": (100, 150),
        }

        optimal_range = platform_optimal.get(platform, (100, 150))
        if char_count < optimal_range[0]:
            improvements.append(
                f"📏 Caption is short ({char_count} chars). Optimal: {optimal_range[0]}-{optimal_range[1]}"
            )
            score -= 5
        elif char_count > optimal_range[1] * 2:
            improvements.append(
                f"📏 Caption is long ({char_count} chars). Consider shortening."
            )
            score -= 5
        else:
            score += 10

        # Check for call-to-action
        cta_patterns = [
            r"\bclick\b",
            r"\btap\b",
            r"\bswipe\b",
            r"\bcomment\b",
            r"\bshare\b",
            r"\btag\b",
            r"\bfollow\b",
            r"\bsave\b",
            r"\blink in bio\b",
            r"\bcheck out\b",
            r"\blearn more\b",
            r"\?$",  # Ends with question
        ]

        has_cta = any(re.search(p, text.lower()) for p in cta_patterns)
        if has_cta:
            score += 10
            improvements.append("✅ Call-to-action detected")
        else:
            improvements.append(
                "💡 Add a call-to-action (question, share, click, etc.)"
            )
            score -= 5

        # Check for emojis
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"
            "\U0001f300-\U0001f5ff"
            "\U0001f680-\U0001f6ff"
            "\U0001f1e0-\U0001f1ff"
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )

        has_emoji = bool(emoji_pattern.search(text))
        if has_emoji:
            score += 5
        else:
            improvements.append("💡 Consider adding emojis for engagement")

        # Generate hashtags
        suggested_hashtags = []
        if include_hashtags:
            suggested_hashtags = self.suggest_hashtags(
                text + " " + niche, platform=platform
            )

            if suggested_hashtags:
                score += 10

                # Add hashtags to optimized text
                hashtag_str = " ".join(f"#{tag}" for tag in suggested_hashtags)
                optimized = f"{text}\n\n{hashtag_str}"

        # Clamp score
        score = max(0, min(100, score))

        return SEOAnalysis(
            original_text=text,
            optimized_text=optimized,
            keywords_found=keywords_data,
            suggested_hashtags=suggested_hashtags,
            score=score,
            improvements=improvements,
        )

    def keyword_research(
        self,
        seed_keyword: str,
        depth: int = 2,
    ) -> dict:
        """
        Deep keyword research starting from a seed keyword.

        Args:
            seed_keyword: Starting keyword.
            depth: How many levels of related keywords to explore.

        Returns:
            Dict with keyword clusters and suggestions.
        """
        explored = set()
        clusters = {}

        def explore(keyword: str, current_depth: int):
            if current_depth > depth or keyword in explored:
                return

            explored.add(keyword)

            # Get trend data
            trends = self.get_trends([keyword])

            if trends:
                kd = trends[0]
                clusters[keyword] = {
                    "interest": kd.interest,
                    "trend": kd.trend,
                    "related": kd.related_queries[:5],
                    "rising": kd.rising_queries[:5],
                    "synonyms": kd.synonyms[:5],
                }

                # Explore related keywords
                for related in kd.related_queries[:3]:
                    explore(related, current_depth + 1)

        explore(seed_keyword, 0)

        # Summarize findings
        rising_keywords = [
            kw for kw, data in clusters.items() if data["trend"] == "rising"
        ]

        high_interest = sorted(
            clusters.items(), key=lambda x: x[1]["interest"], reverse=True
        )[:10]

        return {
            "seed": seed_keyword,
            "clusters": clusters,
            "rising_keywords": rising_keywords,
            "top_keywords": [kw for kw, _ in high_interest],
            "total_explored": len(explored),
        }


# Convenience functions
def optimize_caption(text: str, platform: str = "instagram") -> SEOAnalysis:
    """Quick function to optimize a caption."""
    agent = SEOAgent()
    return agent.optimize_caption(text, platform=platform)


def get_hashtags(text: str, platform: str = "instagram") -> list[str]:
    """Quick function to get hashtag suggestions."""
    agent = SEOAgent()
    return agent.suggest_hashtags(text, platform=platform)


def research_keyword(keyword: str) -> dict:
    """Quick function for keyword research."""
    agent = SEOAgent()
    return agent.keyword_research(keyword)
