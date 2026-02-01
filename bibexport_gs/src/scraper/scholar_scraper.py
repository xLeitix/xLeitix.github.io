"""
Main Google Scholar profile scraper with checkpointing and error handling.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml
from selenium.webdriver.remote.webdriver import WebDriver
from tqdm import tqdm

from scraper.selenium_config import create_stealth_driver
from scraper.rate_limiter import RateLimiter, load_rate_limiter_from_config
from parsers.profile_parser import ScholarProfileParser

logger = logging.getLogger(__name__)


class ScholarScraper:
    """Google Scholar profile scraper with rate limiting and checkpointing."""

    def __init__(
        self,
        profile_url: str,
        headless: bool = False,
        config_path: Optional[Path] = None,
        simple_mode: bool = False
    ):
        """
        Initialize Scholar scraper.

        Args:
            profile_url: URL of the Google Scholar profile
            headless: Whether to run browser in headless mode
            config_path: Path to configuration file
            simple_mode: Use simple Selenium instead of undetected-chromedriver
        """
        self.profile_url = profile_url
        self.headless = headless
        self.simple_mode = simple_mode
        self.driver: Optional[WebDriver] = None
        self.parser: Optional[ScholarProfileParser] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path] = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "scraper_config.yaml"

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return {
                'scraping': {
                    'checkpoint_interval': 25,
                    'checkpoint_file': 'checkpoint.json',
                    'timeout': 30,
                    'show_more_wait': 2
                }
            }

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def initialize(self) -> None:
        """Initialize WebDriver, parser, and rate limiter."""
        logger.info("Initializing Scholar scraper...")

        # Create driver
        if self.simple_mode:
            logger.info("Using simple Selenium mode")
            from scraper.simple_selenium import create_simple_driver
            self.driver = create_simple_driver(headless=self.headless)
        else:
            self.driver = create_stealth_driver(headless=self.headless)

        # Initialize parser
        timeout = self.config.get('scraping', {}).get('timeout', 30)
        self.parser = ScholarProfileParser(self.driver, timeout=timeout)

        # Initialize rate limiter
        self.rate_limiter = load_rate_limiter_from_config()

        logger.info("Scraper initialized successfully")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")

    def scrape_profile(
        self,
        extract_details: bool = False,
        checkpoint_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape papers from Google Scholar profile.

        Args:
            extract_details: Whether to visit detail pages for complete info
            checkpoint_file: Path to checkpoint file for resuming

        Returns:
            List of paper dictionaries
        """
        if checkpoint_file is None:
            checkpoint_file = self.config.get('scraping', {}).get(
                'checkpoint_file', 'checkpoint.json'
            )

        # Check for existing checkpoint
        papers = self._load_checkpoint(checkpoint_file)
        if papers:
            logger.info(f"Resuming from checkpoint with {len(papers)} papers")
            resume = True
        else:
            papers = []
            resume = False

        try:
            if not resume:
                # Navigate to profile page
                logger.info(f"Navigating to profile: {self.profile_url}")
                self.driver.get(self.profile_url)
                self.rate_limiter.page_load_delay()

                # Check for CAPTCHA
                if self.parser.is_captcha_page():
                    logger.error("CAPTCHA detected! Please solve it manually.")
                    input("Press Enter after solving CAPTCHA...")

                # Wait for papers table to load
                if not self.parser.wait_for_papers_table():
                    logger.error("Failed to load papers table")
                    return []

                # Load all papers by clicking "Show more"
                papers = self._load_all_papers()

            # Extract details if requested
            if extract_details:
                papers = self._extract_details_for_papers(papers, checkpoint_file)

            # Clean up checkpoint on success
            self._delete_checkpoint(checkpoint_file)
            logger.info(f"Successfully scraped {len(papers)} papers")

            return papers

        except KeyboardInterrupt:
            logger.warning("Scraping interrupted by user")
            self._save_checkpoint(papers, checkpoint_file)
            raise
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            self._save_checkpoint(papers, checkpoint_file)
            raise

    def _load_all_papers(self) -> List[Dict[str, Any]]:
        """
        Load all papers by clicking "Show more" button repeatedly.

        Returns:
            List of papers with basic information
        """
        logger.info("Loading all papers from profile...")

        previous_count = 0
        max_attempts = 100  # Prevent infinite loops

        for attempt in range(max_attempts):
            # Extract current papers
            papers = self.parser.extract_papers_from_table()
            current_count = len(papers)

            if current_count == previous_count:
                # No new papers loaded, we're done
                logger.info(f"All papers loaded (total: {current_count})")
                break

            logger.info(f"Loaded {current_count} papers so far...")
            previous_count = current_count

            # Try to click "Show more"
            if not self.parser.click_show_more():
                # Button not found or disabled, we're done
                logger.info(f"Finished loading papers (total: {current_count})")
                break

            # Wait for new papers to load
            show_more_wait = self.config.get('scraping', {}).get('show_more_wait', 2)
            time.sleep(show_more_wait)

            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            self.rate_limiter.random_delay()

        return papers

    def _extract_details_for_papers(
        self,
        papers: List[Dict[str, Any]],
        checkpoint_file: str
    ) -> List[Dict[str, Any]]:
        """
        Extract detailed information for each paper by visiting detail pages.

        Args:
            papers: List of papers with basic info
            checkpoint_file: Path to checkpoint file

        Returns:
            List of papers with complete information
        """
        logger.info(f"Extracting details for {len(papers)} papers...")

        checkpoint_interval = self.config.get('scraping', {}).get('checkpoint_interval', 25)

        with tqdm(total=len(papers), desc="Extracting paper details") as pbar:
            for idx, paper in enumerate(papers):
                try:
                    # Check if details already extracted (from checkpoint)
                    if paper.get('details_extracted'):
                        pbar.update(1)
                        continue

                    # Apply rate limiting before each request
                    self.rate_limiter.wait_if_needed()

                    # Extract details
                    paper = self.parser.extract_paper_details(paper)
                    paper['details_extracted'] = True

                    # Apply delay after request
                    self.rate_limiter.random_delay()

                    # Check for CAPTCHA
                    if self.parser.is_captcha_page():
                        logger.error("CAPTCHA detected! Saving checkpoint...")
                        self._save_checkpoint(papers, checkpoint_file)
                        input("Press Enter after solving CAPTCHA to continue...")

                    # Save checkpoint periodically
                    if (idx + 1) % checkpoint_interval == 0:
                        self._save_checkpoint(papers, checkpoint_file)
                        logger.info(f"Checkpoint saved at paper {idx + 1}/{len(papers)}")

                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error extracting details for paper {idx}: {e}")
                    pbar.update(1)
                    continue

        return papers

    def _save_checkpoint(self, papers: List[Dict[str, Any]], checkpoint_file: str) -> None:
        """Save checkpoint to file."""
        try:
            checkpoint_path = Path(checkpoint_file)
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            logger.info(f"Checkpoint saved to {checkpoint_file}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    def _load_checkpoint(self, checkpoint_file: str) -> List[Dict[str, Any]]:
        """Load checkpoint from file."""
        checkpoint_path = Path(checkpoint_file)
        if not checkpoint_path.exists():
            return []

        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            logger.info(f"Loaded checkpoint from {checkpoint_file}")
            return papers
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return []

    def _delete_checkpoint(self, checkpoint_file: str) -> None:
        """Delete checkpoint file."""
        checkpoint_path = Path(checkpoint_file)
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                logger.info(f"Deleted checkpoint file: {checkpoint_file}")
            except Exception as e:
                logger.error(f"Error deleting checkpoint: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


def scrape_scholar_profile(
    profile_url: str,
    headless: bool = False,
    extract_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape a Google Scholar profile.

    Args:
        profile_url: URL of the Google Scholar profile
        headless: Whether to run browser in headless mode
        extract_details: Whether to extract detailed information from paper pages

    Returns:
        List of paper dictionaries
    """
    with ScholarScraper(profile_url, headless=headless) as scraper:
        return scraper.scrape_profile(extract_details=extract_details)
