"""
Simple Selenium configuration using webdriver-manager for testing.
"""

import random
import logging
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


def create_simple_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Create a simple Selenium WebDriver using webdriver-manager.

    This is a simpler alternative to undetected-chromedriver for testing.

    Args:
        headless: Whether to run in headless mode

    Returns:
        Configured WebDriver instance
    """
    logger.info(f"Creating simple Chrome driver (headless={headless})")

    # Configure Chrome options
    options = Options()

    # Basic options
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if headless:
        options.add_argument("--headless=new")

    # Create driver using webdriver-manager (handles version matching automatically)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    logger.info("Simple Chrome driver created successfully")
    return driver
