"""
Settings view for the desktop GUI.

Provides configuration for:
- LLM provider and API keys
- Application preferences
- Google Authentication (No API Key)
- Platform Connection Manager (OAuth tokens)
"""

import logging
import os
import subprocess

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.auth import get_google_auth

logger = logging.getLogger(__name__)


class SettingsView(QWidget):
    """Settings view for application configuration."""

    LLM_PROVIDERS = [
        "groq",
        "openrouter",
        "ollama",
        "gemini",
        "vertex_ai",  # Added Vertex AI
        "openai",
        "anthropic",
        "huggingface",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("⚙️ Settings")
        title.setObjectName("h1")
        main_layout.addWidget(title)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(20)

        # === GOOGLE AUTH SECTION ===
        auth_group = QGroupBox("👤 Google Login (No API Key)")
        auth_layout = QVBoxLayout(auth_group)

        info_label = QLabel(
            "Use your Google Account instead of API keys.\n"
            "Supports Gemini CLI ('gcloud') credentials automatically."
        )
        info_label.setStyleSheet("color: #94a3b8; font-style: italic;")
        auth_layout.addWidget(info_label)

        self.auth_status = QLabel("Status: Checking...")
        self.auth_status.setStyleSheet("font-weight: bold;")

        btn_row = QHBoxLayout()
        self.signin_btn = QPushButton("🔵 Sign in with Google")
        self.signin_btn.clicked.connect(self._handle_signin)

        self.logout_btn = QPushButton("Log out")
        self.logout_btn.clicked.connect(self._handle_logout)
        self.logout_btn.hide()

        btn_row.addWidget(self.signin_btn)
        btn_row.addWidget(self.logout_btn)
        btn_row.addStretch()

        auth_layout.addWidget(self.auth_status)
        auth_layout.addLayout(btn_row)
        layout.addWidget(auth_group)
        # ===========================

        # === MULTI-CLIENT BROWSER PROFILES ===
        browser_group = QGroupBox("🌐 Multi-Client Browser Profiles")
        browser_layout = QVBoxLayout(browser_group)

        browser_info = QLabel(
            "Each client has their own browser profile with isolated sessions.\n"
            "One Identity = One Profile. Login once, automate forever."
        )
        browser_info.setStyleSheet("color: #94a3b8; font-style: italic;")
        browser_layout.addWidget(browser_info)

        # Profile Selector Row
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Active Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True)  # Allow typing new client names
        self.profile_combo.setPlaceholderText("Type client name or select...")
        self._refresh_browser_profiles()  # Load existing profiles
        profile_row.addWidget(self.profile_combo, 1)
        browser_layout.addLayout(profile_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()

        login_btn = QPushButton("🔑 Open Browser to Login")
        login_btn.setStyleSheet(
            """
            QPushButton {
                background: linear-gradient(135deg, #34d399, #10b981);
                border: none;
                border-radius: 8px;
                color: white;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #10b981, #059669);
            }
            """
        )
        login_btn.clicked.connect(self._open_manual_browser)
        btn_row.addWidget(login_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #475569;
                border-radius: 8px;
                color: #94a3b8;
                padding: 12px 16px;
            }
            QPushButton:hover {
                border-color: #818cf8;
                color: #c7d2fe;
            }
            """
        )
        refresh_btn.clicked.connect(self._refresh_browser_profiles)
        btn_row.addWidget(refresh_btn)

        browser_layout.addLayout(btn_row)
        layout.addWidget(browser_group)
        # =====================================

        # === CONNECTION MANAGER SECTION ===
        # NOTE: Connection Manager is not yet implemented.
        # The core/connections.py module needs to be created with:
        # - PlatformConnection dataclass
        # - ConnectionManager class with get_connection_manager() singleton
        # - PLATFORM_INFO dictionary
        # For now, showing a placeholder.
        connections_group = QGroupBox("🔗 Platform Connections")
        connections_layout = QVBoxLayout(connections_group)

        conn_info = QLabel(
            "Manage OAuth connections to publish content on social platforms.\n"
            "Connect to enable auto-posting and analytics.\n\n"
            "⚠️ Coming Soon: Connection Manager is under development."
        )
        conn_info.setStyleSheet("color: #94a3b8; font-style: italic;")
        connections_layout.addWidget(conn_info)

        # Placeholder for future implementation
        self.connection_cards: dict[str, object] = {}

        layout.addWidget(connections_group)
        # ==================================

        # LLM Settings
        llm_group = QGroupBox("🧠 LLM Configuration")
        llm_layout = QFormLayout(llm_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(self.LLM_PROVIDERS)
        llm_layout.addRow("Provider:", self.provider_combo)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Auto-select if empty")
        llm_layout.addRow("Model:", self.model_input)

        self.fallback_combo = QComboBox()
        self.fallback_combo.addItems(self.LLM_PROVIDERS)
        llm_layout.addRow("Fallback Provider:", self.fallback_combo)

        layout.addWidget(llm_group)

        # API Keys
        api_group = QGroupBox("🔑 API Keys")
        api_layout = QFormLayout(api_group)

        self.groq_key = QLineEdit()
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key.setPlaceholderText("sk-...")
        api_layout.addRow("Groq:", self.groq_key)

        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key.setPlaceholderText("sk-...")
        api_layout.addRow("OpenRouter:", self.openrouter_key)

        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("sk-...")
        api_layout.addRow("OpenAI:", self.openai_key)

        self.anthropic_key = QLineEdit()
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key.setPlaceholderText("sk-...")
        api_layout.addRow("Anthropic:", self.anthropic_key)

        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Google Gemini API:", self.gemini_key)

        self.hf_token = QLineEdit()
        self.hf_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_token.setPlaceholderText("hf_...")
        api_layout.addRow("Hugging Face:", self.hf_token)

        layout.addWidget(api_group)

        # Ollama Settings
        ollama_group = QGroupBox("🦙 Ollama Settings")
        ollama_layout = QFormLayout(ollama_group)

        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        ollama_layout.addRow("Ollama URL:", self.ollama_url)

        self.ollama_model = QLineEdit()
        self.ollama_model.setPlaceholderText("llama3.2:3b")
        ollama_layout.addRow("Ollama Model:", self.ollama_model)

        layout.addWidget(ollama_group)

        # Social Media Credentials
        social_group = QGroupBox("📱 Social Media")
        social_layout = QFormLayout(social_group)

        self.ig_user = QLineEdit()
        social_layout.addRow("Instagram User:", self.ig_user)

        self.ig_pass = QLineEdit()
        self.ig_pass.setEchoMode(QLineEdit.EchoMode.Password)
        social_layout.addRow("Instagram Pass:", self.ig_pass)

        layout.addWidget(social_group)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("background-color: #e94560; padding: 15px 30px;")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

        # Check initial auth state
        self._update_auth_ui()

    def _update_auth_ui(self):
        auth = get_google_auth()
        creds = auth.get_credentials()

        if creds and creds.valid:
            project_id = auth.get_project_id() or "Unknown Project"
            self.auth_status.setText(f"Status: ✅ Authenticated ({project_id})")
            self.auth_status.setStyleSheet("font-weight: bold; color: #34d399;")
            self.signin_btn.hide()
            self.logout_btn.show()

            # Auto-switch to Vertex AI if Gemini is selected
            if self.provider_combo.currentText() == "gemini":
                self.provider_combo.setCurrentText("vertex_ai")
        else:
            self.auth_status.setText("Status: Not Signed In")
            self.auth_status.setStyleSheet("font-weight: bold; color: #f87171;")
            self.signin_btn.show()
            self.logout_btn.hide()

    def _handle_signin(self):
        if get_google_auth().login():
            QMessageBox.information(self, "Success", "Signed in successfully!")
            self._update_auth_ui()
        else:
            QMessageBox.warning(
                self, "Error", "Could not sign in. Ensure client_secrets.json exists."
            )

    def _handle_logout(self):
        get_google_auth().logout()
        self._update_auth_ui()

    def _load_current_settings(self) -> None:
        """Load current settings from environment."""
        self.provider_combo.setCurrentText(os.getenv("LLM_PROVIDER", "groq"))
        self.model_input.setText(os.getenv("LLM_MODEL", ""))
        self.fallback_combo.setCurrentText(os.getenv("LLM_FALLBACK_PROVIDER", "ollama"))

        self.groq_key.setText(os.getenv("GROQ_API_KEY", ""))
        self.openrouter_key.setText(os.getenv("OPENROUTER_API_KEY", ""))
        self.openai_key.setText(os.getenv("OPENAI_API_KEY", ""))
        self.anthropic_key.setText(os.getenv("ANTHROPIC_API_KEY", ""))
        self.gemini_key.setText(os.getenv("GEMINI_API_KEY", ""))
        self.hf_token.setText(os.getenv("HF_TOKEN", ""))

        self.ollama_url.setText(os.getenv("OLLAMA_URL", "http://localhost:11434"))
        self.ollama_model.setText(os.getenv("OLLAMA_MODEL", "llama3.2:3b"))

        self.ig_user.setText(os.getenv("INSTAGRAM_USERNAME", ""))
        self.ig_pass.setText(os.getenv("INSTAGRAM_PASSWORD", ""))

    def _save_settings(self) -> None:
        """Save settings to .env file."""
        try:
            # Find .env file
            env_path = os.path.join(os.getcwd(), ".env")

            # Build new content
            lines = []
            lines.append(f"LLM_PROVIDER={self.provider_combo.currentText()}")
            lines.append(f"LLM_MODEL={self.model_input.text()}")
            lines.append(f"LLM_FALLBACK_PROVIDER={self.fallback_combo.currentText()}")
            lines.append(f"OLLAMA_MODEL={self.ollama_model.text()}")
            lines.append(f"OLLAMA_URL={self.ollama_url.text()}")
            lines.append("")
            lines.append(f"GROQ_API_KEY={self.groq_key.text()}")
            lines.append(f"OPENROUTER_API_KEY={self.openrouter_key.text()}")
            lines.append(f"OPENAI_API_KEY={self.openai_key.text()}")
            lines.append(f"ANTHROPIC_API_KEY={self.anthropic_key.text()}")
            lines.append(f"GEMINI_API_KEY={self.gemini_key.text()}")
            lines.append(f"HF_TOKEN={self.hf_token.text()}")
            lines.append("")
            lines.append(f"INSTAGRAM_USERNAME={self.ig_user.text()}")
            lines.append(f"INSTAGRAM_PASSWORD={self.ig_pass.text()}")

            with open(env_path, "w") as f:
                f.write("\n".join(lines))

            # Update environment
            os.environ["LLM_PROVIDER"] = self.provider_combo.currentText()
            os.environ["LLM_MODEL"] = self.model_input.text()

            QMessageBox.information(self, "Saved", "Settings saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _reset_defaults(self) -> None:
        """Reset to default values."""
        self.provider_combo.setCurrentText("groq")
        self.model_input.clear()
        self.fallback_combo.setCurrentText("ollama")
        self.ollama_url.setText("http://localhost:11434")
        self.ollama_model.setText("llama3.2:3b")

    # === CONNECTION MANAGER HANDLERS ===
    # NOTE: These handlers are stubs - Connection Manager is not implemented yet.
    # They will be functional once core/connections.py is created.

    def _handle_platform_connect(self, platform: str) -> None:
        """Handle connect button click for a platform. (Stub)"""
        _ = platform  # Suppress unused warning
        QMessageBox.information(
            self,
            "Coming Soon",
            "Connection Manager is under development.\n\n"
            "Platform connections will be available in a future update.",
        )

    def _handle_platform_disconnect(self, platform: str) -> None:
        """Handle disconnect button click for a platform. (Stub)"""
        _ = platform
        pass

    def _handle_platform_refresh(self, platform: str) -> None:
        """Handle refresh button click for a platform. (Stub)"""
        _ = platform
        pass

    def _refresh_connection_card(self, platform: str) -> None:
        """Refresh the UI for a specific platform card. (Stub)"""
        _ = platform
        pass

    def _refresh_all_connections(self) -> None:
        """Refresh all connection cards. (Stub)"""
        pass

    def _run_auth_command(self, platform: str) -> None:
        """Run authentication command for a platform."""
        try:
            # Open a terminal with the auth command
            cmd = f"python -m social_media_manager auth {platform}"

            # Try different terminal emulators
            terminals = [
                [
                    "gnome-terminal",
                    "--",
                    "bash",
                    "-c",
                    f"{cmd}; read -p 'Press Enter to close'",
                ],
                [
                    "konsole",
                    "-e",
                    "bash",
                    "-c",
                    f"{cmd}; read -p 'Press Enter to close'",
                ],
                ["xterm", "-e", f"bash -c '{cmd}; read -p \"Press Enter to close\"'"],
            ]

            for terminal_cmd in terminals:
                try:
                    subprocess.Popen(terminal_cmd)
                    logger.info(f"Launched auth command in terminal: {cmd}")
                    return
                except FileNotFoundError:
                    continue

            # Fallback: show command to run manually
            QMessageBox.information(
                self,
                "Run Authentication",
                f"Please run this command in a terminal:\n\n{cmd}",
            )

        except Exception as e:
            logger.error(f"Failed to run auth command: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not launch terminal.\n\nPlease run manually:\n{cmd}",
            )

    def _open_manual_browser(self) -> None:
        """Opens a persistent browser for manual login to social platforms."""
        try:
            import asyncio
            import threading

            from ...config import config

            # Get profile from combo box (allows new client names)
            profile_name = self.profile_combo.currentText().strip() or "default"
            profile_dir = config.BROWSER_PROFILES_DIR / profile_name
            profile_dir.mkdir(parents=True, exist_ok=True)

            QMessageBox.information(
                self,
                "Manual Login Mode",
                f"Opening browser for profile: '{profile_name}'\n\n"
                "1. Log in to Facebook, LinkedIn, Instagram, TikTok, etc.\n"
                "2. Check 'Remember me' / 'Keep me signed in'\n"
                "3. Close the browser window when done.\n\n"
                "Your session will be saved for automated posting.",
            )

            async def run_login() -> None:
                try:
                    from playwright.async_api import async_playwright

                    async with async_playwright() as p:
                        # Launch persistent context (saves cookies/session)
                        context = await p.chromium.launch_persistent_context(
                            user_data_dir=str(profile_dir),
                            headless=False,
                            args=[
                                "--disable-blink-features=AutomationControlled",
                                "--start-maximized",
                            ],
                            viewport=None,  # Use full screen
                        )
                        page = await context.new_page()
                        await page.goto("https://www.google.com")

                        # Keep browser open until user closes it
                        try:
                            await page.wait_for_event("close", timeout=0)
                        except Exception:
                            pass  # User closed the browser

                        await context.close()
                except ImportError:
                    logger.error(
                        "Playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                except Exception as e:
                    logger.error(f"Browser launch failed: {e}")

            # Run in background thread to avoid freezing GUI
            def run_async() -> None:
                asyncio.run(run_login())

            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"Failed to open manual browser: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not launch browser: {e}\n\n"
                "Make sure Playwright is installed:\n"
                "pip install playwright && playwright install chromium",
            )

    def _refresh_browser_profiles(self) -> None:
        """Scan browser_profiles folder for existing profiles."""
        from ...config import config

        self.profile_combo.clear()
        self.profile_combo.addItem("default")

        if config.BROWSER_PROFILES_DIR.exists():
            for p in config.BROWSER_PROFILES_DIR.iterdir():
                if p.is_dir() and p.name != "default":
                    self.profile_combo.addItem(p.name)
