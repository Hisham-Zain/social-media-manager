"""
HybridBrain: Unified LLM interface using LiteLLM.

Provides a single API for 100+ LLM providers with automatic fallback.
"""

import json
import os
from typing import Any, Optional

from loguru import logger

from ..config import config

# NOTE: Removed top-level import of get_google_auth to prevent circular dependency

# Configure LiteLLM
try:
    import litellm
    from litellm import completion

    LITELLM_AVAILABLE = True
    # Suppress LiteLLM debug logs
    litellm.set_verbose = False
except ImportError:
    LITELLM_AVAILABLE = False

# Legacy Groq import for backward compatibility
try:
    from groq import Groq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Import WebSearcher for search-enhanced thinking
try:
    from .searcher import WebSearcher

    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# Provider to model mapping (default models for each provider)
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini/gemini-1.5-flash",
    "vertex_ai": "vertex_ai/gemini-1.5-flash",
    "ollama": "ollama/llama3.2:3b",
    "cohere": "command-r-plus",
    "openrouter": "openrouter/google/gemini-flash-1.5",
    "perplexity": "perplexity/sonar-pro",
}

# Provider to API key env variable mapping
PROVIDER_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "cohere": "COHERE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}


class HybridBrain:
    """
    The central intelligence engine using LiteLLM for unified LLM access.

    Supports 100+ LLM providers with automatic fallback and consistent API.
    """

    def __init__(self) -> None:
        """Initialize HybridBrain with configured provider."""
        self.provider = config.LLM_PROVIDER.lower()
        self.fallback_provider = config.LLM_FALLBACK_PROVIDER.lower()
        self.fallback2_provider = getattr(
            config, "LLM_FALLBACK2_PROVIDER", "ollama"
        ).lower()

        # === GOOGLE AUTH AUTO-DETECTION ===
        self._configure_google_auth()
        # ==================================

        # Build model strings for 3-tier fallback chain
        self.model = self._build_model_string(
            self.provider, config.LLM_MODEL or DEFAULT_MODELS.get(self.provider, "")
        )
        self.fallback_model = self._build_model_string(
            self.fallback_provider,
            config.LLM_FALLBACK_MODEL or DEFAULT_MODELS.get(self.fallback_provider, ""),
        )
        self.fallback2_model = self._build_model_string(
            self.fallback2_provider,
            getattr(config, "LLM_FALLBACK2_MODEL", "")
            or DEFAULT_MODELS.get(self.fallback2_provider, "llama3.2:3b"),
        )

        # Determine mode
        if LITELLM_AVAILABLE:
            self.mode = "litellm"
            self._configure_litellm()
            logger.info(f"🧠 Brain Mode: LiteLLM ({self.provider} → {self.model})")
        elif GROQ_AVAILABLE and config.GROQ_API_KEY:
            # Fallback to legacy Groq client
            self.mode = "groq"
            self.groq_client = Groq(api_key=config.GROQ_API_KEY)
            logger.info("🧠 Brain Mode: GROQ (Legacy)")
        else:
            self.mode = "ollama"
            logger.info(f"🧠 Brain Mode: OLLAMA ({config.OLLAMA_MODEL})")

    def _configure_google_auth(self):
        """Check for Google credentials and setup Vertex AI if needed."""
        # Lazy import to avoid circular dependency loop with core/orchestrator
        from ..core.auth import get_google_auth

        auth = get_google_auth()
        creds = auth.get_credentials()

        if creds and creds.valid:
            # If requesting Gemini/Vertex but no API Key is set, auto-enable Vertex AI
            if (
                self.provider == "gemini" and not config.GEMINI_API_KEY
            ) or self.provider == "vertex_ai":
                logger.info(
                    "🧠 Brain: Using Google Account (Vertex AI) for generation."
                )
                self.provider = "vertex_ai"

                # 1. Point to token file if using In-App login
                if auth.token_path.exists():
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(auth.token_path)

                # 2. Set Project ID (Crucial for Vertex AI)
                project_id = auth.get_project_id()
                if project_id:
                    os.environ["VERTEXAI_PROJECT"] = project_id
                    os.environ["VERTEXAI_LOCATION"] = "us-central1"  # Default
                    logger.info(f"🧠 Vertex AI configured for project: {project_id}")

    def _build_model_string(self, provider: str, model: str) -> str:
        """Build a LiteLLM-compatible model string."""
        provider = provider.lower()

        # If model already has provider prefix, return as-is
        if "/" in model:
            return model

        # Providers that don't need prefix
        if provider in ["openai"]:
            return model

        # Vertex AI special handling
        if provider == "vertex_ai" and not model.startswith("vertex_ai/"):
            return f"vertex_ai/{model}"

        # Add provider prefix for others
        return f"{provider}/{model}"

    def _configure_litellm(self) -> None:
        """Configure LiteLLM with API keys and settings."""
        # Set API keys from config (LiteLLM also reads from env automatically)
        if config.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
        if config.ANTHROPIC_API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = config.ANTHROPIC_API_KEY
        if config.GROQ_API_KEY:
            os.environ["GROQ_API_KEY"] = config.GROQ_API_KEY
        if config.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = config.GEMINI_API_KEY
        if config.COHERE_API_KEY:
            os.environ["COHERE_API_KEY"] = config.COHERE_API_KEY
        if config.PERPLEXITY_API_KEY:
            os.environ["PERPLEXITY_API_KEY"] = config.PERPLEXITY_API_KEY

        # Configure Ollama base URL if using Ollama
        if self.provider == "ollama" or self.fallback_provider == "ollama":
            os.environ["OLLAMA_API_BASE"] = config.OLLAMA_URL

    def think(self, prompt: str, context: str = "", json_mode: bool = False) -> str:
        """
        Process a prompt and return the AI's response.

        If USE_REMOTE_BRAIN is enabled, delegates to the remote Brain Box API.
        Otherwise, uses local LLM providers.
        """
        # Check for remote brain mode first
        if getattr(config, "USE_REMOTE_BRAIN", False):
            return self._think_remote(prompt, context, json_mode)

        # Local processing
        if self.mode == "litellm":
            return self._think_litellm(prompt, context, json_mode)
        elif self.mode == "groq":
            return self._think_groq(prompt, context, json_mode)
        return self._think_ollama(prompt, context, json_mode)

    def _think_remote(self, prompt: str, context: str, json_mode: bool) -> str:
        """Send inference request to remote Brain Box API."""
        import requests

        try:
            api_url = getattr(config, "BRAIN_API_URL", "http://localhost:8000")
            timeout = getattr(config, "BRAIN_API_TIMEOUT", 120)

            logger.info(f"🧠 Remote Brain: Sending request to {api_url}")

            response = requests.post(
                f"{api_url}/api/v1/brain/think",
                json={
                    "prompt": prompt,
                    "context": context,
                    "json_mode": json_mode,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data.get("response", "")
            else:
                error = data.get("error", "Unknown error")
                logger.error(f"❌ Remote Brain error: {error}")
                # Fallback to local if remote fails
                logger.info("🔄 Falling back to local brain...")
                return self._think_local(prompt, context, json_mode)

        except requests.exceptions.ConnectionError:
            logger.error(
                f"❌ Remote Brain offline at {api_url}. Using local fallback..."
            )
            return self._think_local(prompt, context, json_mode)
        except requests.exceptions.Timeout:
            logger.error("❌ Remote Brain timeout. Using local fallback...")
            return self._think_local(prompt, context, json_mode)
        except Exception as e:
            logger.error(f"❌ Remote Brain failed: {e}. Using local fallback...")
            return self._think_local(prompt, context, json_mode)

    def _think_local(self, prompt: str, context: str, json_mode: bool) -> str:
        """Local processing fallback (used when remote brain fails)."""
        if self.mode == "litellm":
            return self._think_litellm(prompt, context, json_mode)
        elif self.mode == "groq":
            return self._think_groq(prompt, context, json_mode)
        return self._think_ollama(prompt, context, json_mode)

    def _think_litellm(self, prompt: str, context: str, json_mode: bool) -> str:
        """Execute thinking using LiteLLM."""
        messages = [
            {"role": "system", "content": context or "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # Parse specific API errors from LiteLLM exceptions
            error_str = str(e).lower()
            if (
                "authentication" in error_str
                or "api key" in error_str
                or "401" in error_str
            ):
                logger.error(
                    f"❌ Primary LLM Auth Error ({self.model}): Invalid API Key/Creds. Check your .env or sign in."
                )
            elif (
                "rate limit" in error_str or "429" in error_str or "quota" in error_str
            ):
                logger.error(
                    f"❌ Primary LLM Rate Limit ({self.model}): Too many requests. Trying fallback..."
                )
            else:
                logger.error(f"❌ Primary LLM ({self.model}) failed: {e}")
            return self._fallback_litellm(messages, json_mode)

    def _fallback_litellm(self, messages: list, json_mode: bool) -> str:
        """Fallback chain: Try fallback1 (Groq), then fallback2 (Ollama)."""
        # Try first fallback (Groq)
        try:
            logger.info(f"🔄 Trying fallback 1: {self.fallback_model}")
            response = completion(
                model=self.fallback_model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"❌ Fallback 1 ({self.fallback_model}) failed: {e}")

        # Try second fallback (Ollama - local)
        try:
            logger.info(f"🔄 Trying fallback 2: {self.fallback2_model}")
            response = completion(
                model=self.fallback2_model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"❌ Fallback 2 ({self.fallback2_model}) also failed: {e}")
            return (
                "{}"
                if json_mode
                else "Error: All LLM providers offline (tried Gemini → Groq → Ollama)."
            )

    def _think_groq(self, prompt: str, context: str, json_mode: bool) -> str:
        """Legacy Groq implementation for backward compatibility."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": context or "You are a helpful AI assistant.",
                },
                {"role": "user", "content": prompt},
            ]
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"❌ Groq Failed: {e}. Falling back to Ollama...")
            return self._think_ollama(prompt, context, json_mode)

    def _think_ollama(self, prompt: str, context: str, json_mode: bool) -> str:
        """Fallback to local Ollama using message list format."""
        import requests

        messages = [
            {"role": "system", "content": context or "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "format": "json" if json_mode else None,
        }
        try:
            res = requests.post(
                f"{config.OLLAMA_URL}/api/chat",
                json=payload,
                timeout=60,
            )
            res.raise_for_status()
            # Chat API returns message.content instead of response
            return res.json().get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            # Specific Ollama connection error with helpful hint
            logger.error(
                f"❌ Ollama is not running! Start it with: ollama serve\n"
                f"   Then ensure model '{config.OLLAMA_MODEL}' is available: ollama pull {config.OLLAMA_MODEL}"
            )
        except Exception as e:
            logger.error(f"❌ Ollama Error: {e}")
        return (
            "{}"
            if json_mode
            else "Error: Brain offline. Ensure Ollama is running (ollama serve)."
        )

    # --- MCP TOOL INTEGRATION ---

    async def think_with_tools(
        self,
        prompt: str,
        context: str = "",
        max_tool_calls: int = 5,
    ) -> str:
        """
        Process a prompt with MCP tools available for function calling.

        The LLM can request tool calls, which are executed via MCP servers,
        and results are fed back to the LLM for a final response.

        Args:
            prompt: User prompt
            context: System context
            max_tool_calls: Maximum number of tool call iterations

        Returns:
            Final LLM response after tool execution
        """
        if not LITELLM_AVAILABLE:
            return self.think(prompt, context)

        # Lazy import MCP to avoid startup overhead
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()
        except ImportError:
            logger.warning("MCP client not available")
            return self.think(prompt, context)

        # Get tools in OpenAI format
        tools = manager.get_tools_for_llm()
        if not tools:
            logger.debug("No MCP tools available, falling back to standard think")
            return self.think(prompt, context)

        messages = [
            {"role": "system", "content": context or "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ]

        tool_call_count = 0

        while tool_call_count < max_tool_calls:
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

                message = response.choices[0].message

                # Check if LLM wants to call tools
                if not message.tool_calls:
                    # No more tool calls, return final response
                    return message.content or ""

                # Add assistant message with tool calls
                messages.append(message.model_dump())

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    # Parse server.tool_name format
                    if "_" in tool_name:
                        parts = tool_name.split("_", 1)
                        server_name = parts[0]
                        actual_tool_name = parts[1] if len(parts) > 1 else tool_name
                    else:
                        server_name = tool_name
                        actual_tool_name = tool_name

                    logger.info(f"🔧 MCP Tool Call: {server_name}.{actual_tool_name}")

                    # Call the tool via MCP
                    result = await manager.call_tool(
                        server_name, actual_tool_name, tool_args
                    )

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result),
                        }
                    )

                    tool_call_count += 1

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                # Fall back to standard thinking
                return self.think(prompt, context)

        # Max tool calls reached, get final response
        try:
            response = completion(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Final response failed: {e}")
            return self.think(prompt, context)

    def get_mcp_tools_description(self) -> str:
        """Get human-readable description of available MCP tools."""
        try:
            from ..core.mcp_client import get_mcp_manager

            return get_mcp_manager().get_tool_descriptions()
        except ImportError:
            return "MCP tools not available"

    # --- SKILLS ---
    def generate_client_content(self, context: str, topic: str, platform: str) -> str:
        """Generate viral content for a specific platform."""
        return self.think(
            f"Write a viral {platform} post about: {topic}",
            context=f"{context}\nReturn only the caption text.",
        )

    def extract_visual_keywords(self, transcript_segment: str) -> str:
        """Extract visual keywords from transcript for stock photo search."""
        prompt = f"Convert this transcript segment into a search query for a stock photo/B-roll. Return ONLY the search query words.\n\nSegment: '{transcript_segment}'"
        return self.think(prompt).replace('"', "").strip()

    def generate_viral_hooks(self, topic: str) -> dict[str, Any]:
        """
        Generate multiple viral hook variations for a topic.
        """
        prompt = f"Topic: '{topic}'. Generate 5 Viral Hooks (First 3s). Styles: Negativity, Curiosity, Contrarian, Listicle, Story. JSON Output: {{ 'hooks': [ {{'style': '...', 'text': '...'}} ] }}"
        try:
            res = self.think(prompt, json_mode=True)
            return json.loads(res)
        except Exception as e:
            logger.error(f"❌ Brain: Failed to generate hooks: {e}")
            return {"hooks": [], "error": "AI Error"}

    # --- WEB SEARCH ENHANCED THINKING ---

    def search_and_think(
        self,
        query: str,
        prompt: Optional[str] = None,
        max_results: int = 3,
    ) -> str:
        """
        Search the web and then think about the results.
        """
        if not SEARCH_AVAILABLE:
            logger.warning("⚠️ Web search not available")
            return self.think(prompt or f"Provide information about: {query}")

        searcher = WebSearcher()
        results = searcher.search(query, max_results=max_results)

        if not results:
            return self.think(prompt or f"Provide information about: {query}")

        # Build context from search results
        search_context = "Web Search Results:\n"
        for i, result in enumerate(results, 1):
            search_context += f"\n{i}. {result.get('title', '')}\n"
            search_context += f"   {result.get('body', '')[:200]}\n"

        final_prompt = (
            prompt
            or f"Based on the search results, provide a comprehensive answer about: {query}"
        )

        logger.info(f"🔍🧠 Search-enhanced thinking for: {query[:50]}")
        return self.think(
            final_prompt,
            context=f"You have access to recent web search results. Use them to provide accurate, up-to-date information.\n\n{search_context}",
        )

    def research_topic(self, topic: str) -> dict:
        """
        Comprehensive research on a topic using web search.
        """
        if not SEARCH_AVAILABLE:
            return {"topic": topic, "error": "Web search not available"}

        searcher = WebSearcher()
        research = searcher.research_topic(topic)

        # Get AI analysis of research
        research["ai_analysis"] = self.search_and_think(
            topic,
            prompt=f"Analyze the following research about '{topic}' and provide key insights, trends, and recommendations.",
        )

        return research

    # --- UTILITY METHODS ---

    def get_available_providers(self) -> list[dict]:
        """
        Get list of available LLM providers with their status.
        """
        providers = [
            {
                "name": "OpenAI",
                "id": "openai",
                "available": bool(config.OPENAI_API_KEY),
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            },
            {
                "name": "Anthropic",
                "id": "anthropic",
                "available": bool(config.ANTHROPIC_API_KEY),
                "models": [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-haiku-20240307",
                ],
            },
            {
                "name": "Groq",
                "id": "groq",
                "available": bool(config.GROQ_API_KEY),
                "models": [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768",
                ],
            },
            {
                "name": "Google Gemini",
                "id": "gemini",
                "available": bool(config.GEMINI_API_KEY),
                "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
            },
            {
                "name": "Vertex AI (Google Auth)",
                "id": "vertex_ai",
                "available": bool(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    or os.getenv("GOOGLE_CLOUD_PROJECT")
                ),
                "models": ["vertex_ai/gemini-1.5-flash", "vertex_ai/gemini-1.5-pro"],
            },
            {
                "name": "Cohere",
                "id": "cohere",
                "available": bool(config.COHERE_API_KEY),
                "models": ["command-r-plus", "command-r", "command"],
            },
            {
                "name": "Perplexity AI",
                "id": "perplexity",
                "available": bool(config.PERPLEXITY_API_KEY),
                "models": ["sonar-pro", "sonar", "sonar-reasoning"],
            },
            {
                "name": "Ollama (Local)",
                "id": "ollama",
                "available": True,
                "models": ["llama3.2:3b", "llama3.2:1b", "mistral", "codellama"],
            },
        ]
        return providers

    def get_status(self) -> dict:
        """
        Get current brain status.
        """
        return {
            "mode": self.mode,
            "provider": self.provider,
            "model": self.model,
            "fallback_provider": self.fallback_provider,
            "fallback_model": self.fallback_model,
            "litellm_available": LITELLM_AVAILABLE,
            "search_available": SEARCH_AVAILABLE,
        }
