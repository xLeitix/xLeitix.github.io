"""
Selenium WebDriver configuration with anti-detection measures for scraping Google Scholar.
"""

import random
import logging
from pathlib import Path
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class SeleniumConfig:
    """Configuration manager for Selenium WebDriver with anti-detection features."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize Selenium configuration.

        Args:
            config_dir: Path to configuration directory containing user_agents.txt
        """
        if config_dir is None:
            # Default to config/ directory relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self.user_agents = self._load_user_agents()

    def _load_user_agents(self) -> list[str]:
        """Load user agent strings from config file."""
        user_agents_file = self.config_dir / "user_agents.txt"

        if not user_agents_file.exists():
            logger.warning(f"User agents file not found: {user_agents_file}")
            # Fallback to default user agents
            return [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]

        with open(user_agents_file, 'r') as f:
            agents = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded {len(agents)} user agents from {user_agents_file}")
        return agents

    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)

    def _build_chrome_options(self, headless: bool, user_agent: str) -> uc.ChromeOptions:
        """Build a fresh ChromeOptions instance."""
        options = uc.ChromeOptions()

        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")

        if headless:
            options.add_argument("--headless=new")
            logger.info("Running in headless mode")

        return options

    def create_stealth_driver(
        self,
        headless: bool = False,
        user_agent: Optional[str] = None
    ) -> WebDriver:
        """
        Create a Selenium WebDriver with anti-detection configuration.

        Args:
            headless: Whether to run in headless mode
            user_agent: Specific user agent to use (random if None)

        Returns:
            Configured WebDriver instance
        """
        if user_agent is None:
            user_agent = self.get_random_user_agent()

        logger.info(f"Creating stealth driver (headless={headless})")
        logger.debug(f"Using user agent: {user_agent}")

        # Create undetected Chrome driver
        # undetected-chromedriver automatically handles many anti-detection measures
        # Try with explicit version_main first (matching installed Chrome), then auto-detect
        try:
            options = self._build_chrome_options(headless, user_agent)
            driver = uc.Chrome(options=options, version_main=142, use_subprocess=True)
        except Exception as e:
            logger.warning(f"First attempt (version_main=142) failed: {e}. Trying auto-detect...")
            options = self._build_chrome_options(headless, user_agent)
            driver = uc.Chrome(options=options, use_subprocess=True)

        # Additional JavaScript to mask automation
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            """
        })

        logger.info("Stealth driver created successfully")
        return driver


def create_stealth_driver(
    headless: bool = False,
    user_agent: Optional[str] = None,
    config_dir: Optional[Path] = None
) -> WebDriver:
    """
    Factory function to create a stealth WebDriver.

    Args:
        headless: Whether to run in headless mode
        user_agent: Specific user agent to use (random if None)
        config_dir: Path to configuration directory

    Returns:
        Configured WebDriver instance
    """
    config = SeleniumConfig(config_dir=config_dir)
    return config.create_stealth_driver(headless=headless, user_agent=user_agent)
