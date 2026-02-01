"""
CORE conference rankings fetcher and matcher.
"""

import json
import logging
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from io import StringIO

import requests
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class CoreRankingsFetcher:
    """Fetcher for CORE conference rankings with caching and fuzzy matching."""

    CORE_EXPORT_URL = "https://portal.core.edu.au/conf-ranks/?search=&by=all&sort=arank&page=1&do=Export"

    def __init__(self, cache_dir: Optional[Path] = None, cache_days: int = 30):
        """
        Initialize CORE rankings fetcher.

        Args:
            cache_dir: Directory for caching rankings (default: data/)
            cache_days: Number of days before cache expires
        """
        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / "data"

        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "core_rankings_cache.json"
        self.cache_days = cache_days
        self.rankings: Dict[str, Dict] = {}

    def load_rankings(self, force_refresh: bool = False) -> bool:
        """
        Load CORE rankings from cache or fetch from web.

        Args:
            force_refresh: Force refresh from web even if cache is valid

        Returns:
            True if rankings loaded successfully
        """
        # Try to load from cache first
        if not force_refresh and self._load_from_cache():
            logger.info("Loaded CORE rankings from cache")
            return True

        # Fetch from web
        logger.info("Fetching CORE rankings from web...")
        if self._fetch_from_web():
            self._save_to_cache()
            logger.info("CORE rankings fetched and cached successfully")
            return True

        logger.error("Failed to load CORE rankings")
        return False

    def _load_from_cache(self) -> bool:
        """Load rankings from cache file if valid."""
        if not self.cache_file.exists():
            logger.info("Cache file not found")
            return False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check cache age
            last_updated = datetime.fromisoformat(data.get('last_updated', '2000-01-01'))
            cache_age = datetime.now() - last_updated

            if cache_age > timedelta(days=self.cache_days):
                logger.info(f"Cache expired (age: {cache_age.days} days)")
                return False

            self.rankings = data.get('conferences', {})
            logger.info(f"Loaded {len(self.rankings)} conferences from cache")
            return True

        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return False

    def _fetch_from_web(self) -> bool:
        """Fetch rankings from CORE website."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(self.CORE_EXPORT_URL, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse CSV response
            csv_content = response.text
            self._parse_csv(csv_content)

            logger.info(f"Fetched {len(self.rankings)} conferences from CORE")
            return True

        except Exception as e:
            logger.error(f"Error fetching from web: {e}")
            return False

    def _parse_csv(self, csv_content: str) -> None:
        """Parse CSV content into rankings dictionary."""
        # CORE CSV format: ID,Title,Acronym,Source,Rank,HasData,FoR1,FoR2,FoR3
        csv_reader = csv.reader(StringIO(csv_content))
        self.rankings = {}

        for row in csv_reader:
            try:
                # Skip empty rows
                if not row or len(row) < 5:
                    continue

                # Extract fields by position
                title = row[1].strip() if len(row) > 1 else ''
                acronym = row[2].strip() if len(row) > 2 else ''
                rank = row[4].strip() if len(row) > 4 else ''

                if not title or not rank:
                    continue

                # Store by acronym (primary key) and title (secondary)
                conference = {
                    'title': title,
                    'acronym': acronym,
                    'rank': rank
                }

                # Index by acronym if available
                if acronym:
                    self.rankings[acronym.upper()] = conference

                # Also index by title (for fuzzy matching)
                self.rankings[title] = conference

            except Exception as e:
                logger.warning(f"Error parsing CSV row: {e}")
                continue

    def _save_to_cache(self) -> None:
        """Save rankings to cache file."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            data = {
                'last_updated': datetime.now().isoformat(),
                'conferences': self.rankings
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.rankings)} conferences to cache")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def find_ranking(self, venue: str, threshold: int = 80) -> Optional[str]:
        """
        Find CORE ranking for a venue using exact and fuzzy matching.

        Args:
            venue: Venue name or acronym
            threshold: Minimum fuzzy match score (0-100)

        Returns:
            Ranking (A*, A, B, C) or None if not found
        """
        if not venue or not self.rankings:
            return None

        venue = venue.strip()

        # Try exact match on acronym (case-insensitive)
        acronym_match = self.rankings.get(venue.upper())
        if acronym_match:
            logger.debug(f"Exact acronym match for '{venue}': {acronym_match['rank']}")
            return acronym_match['rank']

        # Try exact match on title
        title_match = self.rankings.get(venue)
        if title_match:
            logger.debug(f"Exact title match for '{venue}': {title_match['rank']}")
            return title_match['rank']

        # Try fuzzy matching on all titles and acronyms
        all_keys = list(self.rankings.keys())
        result = process.extractOne(
            venue,
            all_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )

        if result:
            matched_key, score, _ = result
            ranking = self.rankings[matched_key]['rank']
            logger.debug(
                f"Fuzzy match for '{venue}': '{matched_key}' "
                f"(score: {score}, rank: {ranking})"
            )
            return ranking

        logger.debug(f"No ranking found for '{venue}'")
        return None

    def find_ranking_with_details(
        self,
        venue: str,
        threshold: int = 80
    ) -> Optional[Dict[str, any]]:
        """
        Find CORE ranking with match details.

        Args:
            venue: Venue name or acronym
            threshold: Minimum fuzzy match score

        Returns:
            Dictionary with rank, matched_name, confidence, or None
        """
        if not venue or not self.rankings:
            return None

        venue = venue.strip()

        # Try exact match on acronym
        acronym_match = self.rankings.get(venue.upper())
        if acronym_match:
            return {
                'rank': acronym_match['rank'],
                'matched_name': acronym_match['title'],
                'matched_acronym': acronym_match['acronym'],
                'confidence': 100,
                'match_type': 'exact_acronym'
            }

        # Try exact match on title
        title_match = self.rankings.get(venue)
        if title_match:
            return {
                'rank': title_match['rank'],
                'matched_name': title_match['title'],
                'matched_acronym': title_match['acronym'],
                'confidence': 100,
                'match_type': 'exact_title'
            }

        # Try fuzzy matching
        all_keys = list(self.rankings.keys())
        result = process.extractOne(
            venue,
            all_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )

        if result:
            matched_key, score, _ = result
            conference = self.rankings[matched_key]
            return {
                'rank': conference['rank'],
                'matched_name': conference['title'],
                'matched_acronym': conference['acronym'],
                'confidence': score,
                'match_type': 'fuzzy'
            }

        return None

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded rankings."""
        if not self.rankings:
            return {'total': 0, 'by_rank': {}}

        # Count by rank
        rank_counts = {}
        unique_conferences = set()

        for conf in self.rankings.values():
            # Track unique by title to avoid counting duplicates
            title = conf.get('title')
            if title and title not in unique_conferences:
                unique_conferences.add(title)
                rank = conf.get('rank', 'Unknown')
                rank_counts[rank] = rank_counts.get(rank, 0) + 1

        return {
            'total': len(unique_conferences),
            'by_rank': rank_counts
        }


def get_core_ranking(venue: str, force_refresh: bool = False) -> Optional[str]:
    """
    Convenience function to get CORE ranking for a venue.

    Args:
        venue: Venue name or acronym
        force_refresh: Force refresh from web

    Returns:
        Ranking (A*, A, B, C) or None
    """
    fetcher = CoreRankingsFetcher()
    fetcher.load_rankings(force_refresh=force_refresh)
    return fetcher.find_ranking(venue)
