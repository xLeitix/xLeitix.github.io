"""
Parser for Google Scholar profile pages and paper details.
"""

import logging
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class ScholarProfileParser:
    """Parser for Google Scholar profile pages."""

    def __init__(self, driver: WebDriver, timeout: int = 30):
        """
        Initialize parser.

        Args:
            driver: Selenium WebDriver instance
            timeout: Timeout for page loads in seconds
        """
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def wait_for_papers_table(self) -> bool:
        """
        Wait for the papers table to load.

        Returns:
            True if table loaded, False otherwise
        """
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr.gsc_a_tr"))
            )
            logger.info("Papers table loaded successfully")
            return True
        except TimeoutException:
            logger.error("Timeout waiting for papers table to load")
            return False

    def click_show_more(self) -> bool:
        """
        Click the "Show more" button to load more papers.

        Returns:
            True if button was clicked, False if button not found or disabled
        """
        try:
            # Try to find the "Show more" button
            show_more_button = self.driver.find_element(
                By.CSS_SELECTOR, "button#gsc_bpf_more"
            )

            # Check if button is disabled
            if show_more_button.get_attribute("disabled"):
                logger.info("Show more button is disabled - all papers loaded")
                return False

            # Click the button
            show_more_button.click()
            logger.debug("Clicked 'Show more' button")
            return True

        except NoSuchElementException:
            logger.info("Show more button not found - all papers loaded")
            return False
        except Exception as e:
            logger.warning(f"Error clicking show more button: {e}")
            return False

    def extract_papers_from_table(self) -> list[Dict[str, Any]]:
        """
        Extract paper information from the papers table.

        Returns:
            List of paper dictionaries with basic information
        """
        papers = []

        try:
            # Get all paper rows
            paper_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.gsc_a_tr")
            logger.info(f"Found {len(paper_rows)} paper rows in table")

            for idx, row in enumerate(paper_rows):
                try:
                    paper = self._parse_paper_row(row, idx)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing paper row {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting papers from table: {e}")

        return papers

    def _parse_paper_row(self, row, idx: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single paper row from the table.

        Args:
            row: Selenium WebElement for the row
            idx: Row index for logging

        Returns:
            Paper dictionary or None if parsing fails
        """
        try:
            # Get the title and link
            title_elem = row.find_element(By.CSS_SELECTOR, "a.gsc_a_at")
            title = title_elem.text.strip()
            detail_link = title_elem.get_attribute("href")

            # Get authors and venue (combined in one cell)
            authors_venue_elem = row.find_element(By.CSS_SELECTOR, "div.gs_gray")
            authors = authors_venue_elem.text.strip()

            # Try to get venue from the next gray div
            try:
                venue_elems = row.find_elements(By.CSS_SELECTOR, "div.gs_gray")
                venue = venue_elems[1].text.strip() if len(venue_elems) > 1 else ""
            except:
                venue = ""

            # Get citations
            try:
                citations_elem = row.find_element(By.CSS_SELECTOR, "a.gsc_a_ac")
                citations_text = citations_elem.text.strip()
                citations = int(citations_text) if citations_text and citations_text.isdigit() else 0
            except:
                citations = 0

            # Get year
            try:
                year_elem = row.find_element(By.CSS_SELECTOR, "span.gsc_a_h")
                year_text = year_elem.text.strip()
                year = int(year_text) if year_text and year_text.isdigit() else None
            except:
                year = None

            paper = {
                'title': title,
                'authors': authors,
                'venue': venue,
                'year': year,
                'citations': citations,
                'detail_link': detail_link,
                'row_index': idx
            }

            logger.debug(f"Parsed paper {idx}: {title[:50]}...")
            return paper

        except Exception as e:
            logger.warning(f"Failed to parse paper row {idx}: {e}")
            return None

    def extract_paper_details(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to paper detail page and extract complete information.

        Args:
            paper: Paper dictionary with basic info and detail_link

        Returns:
            Updated paper dictionary with complete information
        """
        if not paper.get('detail_link'):
            logger.warning(f"No detail link for paper: {paper.get('title', 'Unknown')}")
            return paper

        try:
            # Navigate to detail page
            self.driver.get(paper['detail_link'])

            # Wait for detail page to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#gsc_oci_title"))
                )
            except TimeoutException:
                logger.warning(f"Timeout loading detail page for: {paper['title']}")
                return paper

            # Parse detail page
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            # Extract full author list
            authors_field = soup.find('div', class_='gsc_oci_field', string='Authors')
            if authors_field:
                authors_value = authors_field.find_next_sibling('div', class_='gsc_oci_value')
                if authors_value:
                    # Split authors by comma
                    authors_list = [a.strip() for a in authors_value.text.split(',')]
                    paper['authors'] = authors_list

            # Extract publication venue
            venue_field = soup.find('div', class_='gsc_oci_field', string='Publication')
            if not venue_field:
                venue_field = soup.find('div', class_='gsc_oci_field', string='Journal')
            if not venue_field:
                venue_field = soup.find('div', class_='gsc_oci_field', string='Conference')

            if venue_field:
                venue_value = venue_field.find_next_sibling('div', class_='gsc_oci_value')
                if venue_value:
                    paper['venue'] = venue_value.text.strip()

            # Extract year (if not already extracted)
            if not paper.get('year'):
                year_field = soup.find('div', class_='gsc_oci_field', string='Publication date')
                if year_field:
                    year_value = year_field.find_next_sibling('div', class_='gsc_oci_value')
                    if year_value:
                        year_text = year_value.text.strip()
                        # Extract year from date string (e.g., "2020/1/1" or "2020")
                        year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                        if year_match:
                            paper['year'] = int(year_match.group())

            logger.debug(f"Extracted details for: {paper['title'][:50]}...")

        except Exception as e:
            logger.warning(f"Error extracting details for {paper['title']}: {e}")

        return paper

    def is_captcha_page(self) -> bool:
        """
        Check if the current page is a CAPTCHA challenge.

        Returns:
            True if CAPTCHA detected, False otherwise
        """
        try:
            # Check for common CAPTCHA indicators
            page_source = self.driver.page_source.lower()

            captcha_indicators = [
                'captcha',
                'unusual traffic',
                'automated requests',
                'verify you are human',
                'recaptcha'
            ]

            for indicator in captcha_indicators:
                if indicator in page_source:
                    logger.warning(f"CAPTCHA detected (indicator: '{indicator}')")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False

    def normalize_venue_name(self, venue: str) -> str:
        """
        Normalize venue name for better matching with rankings.

        Args:
            venue: Raw venue string

        Returns:
            Normalized venue name
        """
        if not venue:
            return ""

        # Remove common prefixes
        prefixes = [
            'Proceedings of',
            'Proceedings of the',
            'Proc. of',
            'Proc. of the',
            'Proc.',
            'International Conference on',
            'International Conf. on',
            'Int. Conf. on',
            'Int. Conference on',
            'IEEE/ACM',
            'IEEE',
            'ACM',
        ]

        normalized = venue
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()

        # Remove year references (e.g., "ICSE 2020" -> "ICSE")
        normalized = re.sub(r'\b(19|20)\d{2}\b', '', normalized).strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized
