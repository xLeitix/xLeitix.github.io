"""
Journal ranking mapper using pre-configured JSON mapping file.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class JournalRankingMapper:
    """Mapper for journal rankings using JSON configuration."""

    def __init__(self, mapping_file: Optional[Path] = None):
        """
        Initialize journal ranking mapper.

        Args:
            mapping_file: Path to JSON mapping file (default: data/journal_rankings.json)
        """
        if mapping_file is None:
            project_root = Path(__file__).parent.parent.parent
            mapping_file = project_root / "data" / "journal_rankings.json"

        self.mapping_file = Path(mapping_file)
        self.journals: Dict[str, Dict] = {}
        self.aliases: Dict[str, str] = {}
        self.load_mappings()

    def load_mappings(self) -> bool:
        """
        Load journal mappings from JSON file.

        Returns:
            True if loaded successfully
        """
        if not self.mapping_file.exists():
            logger.warning(f"Journal mapping file not found: {self.mapping_file}")
            self._create_default_mapping()
            return False

        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.journals = data.get('journals', {})
            self.aliases = data.get('aliases', {})

            logger.info(
                f"Loaded {len(self.journals)} journals and "
                f"{len(self.aliases)} aliases from {self.mapping_file}"
            )
            return True

        except Exception as e:
            logger.error(f"Error loading journal mappings: {e}")
            return False

    def _create_default_mapping(self) -> None:
        """Create a default mapping file if it doesn't exist."""
        try:
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

            default_data = {
                "journals": {},
                "aliases": {}
            }

            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2)

            logger.info(f"Created default journal mapping file: {self.mapping_file}")

        except Exception as e:
            logger.error(f"Error creating default mapping file: {e}")

    def save_mappings(self) -> bool:
        """
        Save current mappings to JSON file.

        Returns:
            True if saved successfully
        """
        try:
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "journals": self.journals,
                "aliases": self.aliases
            }

            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved journal mappings to {self.mapping_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving journal mappings: {e}")
            return False

    def find_ranking(self, journal_name: str, threshold: int = 85) -> Optional[str]:
        """
        Find ranking for a journal using exact and fuzzy matching.

        Args:
            journal_name: Journal name or abbreviation
            threshold: Minimum fuzzy match score (0-100)

        Returns:
            Ranking (A*, A, B, C, Q1-Q4, etc.) or None
        """
        if not journal_name:
            return None

        journal_name = journal_name.strip()

        # Try exact match on journal names
        if journal_name in self.journals:
            rank = self.journals[journal_name].get('rank')
            logger.debug(f"Exact match for '{journal_name}': {rank}")
            return rank

        # Try exact match on aliases
        if journal_name in self.aliases:
            full_name = self.aliases[journal_name]
            rank = self.journals.get(full_name, {}).get('rank')
            logger.debug(f"Alias match for '{journal_name}' -> '{full_name}': {rank}")
            return rank

        # Normalize journal name for fuzzy matching
        normalized = self._normalize_name(journal_name)

        # Try fuzzy matching on journal names
        journal_keys = list(self.journals.keys())
        if journal_keys:
            result = process.extractOne(
                normalized,
                [self._normalize_name(k) for k in journal_keys],
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold
            )

            if result:
                _, score, idx = result
                matched_key = journal_keys[idx]
                rank = self.journals[matched_key].get('rank')
                logger.debug(
                    f"Fuzzy match for '{journal_name}': '{matched_key}' "
                    f"(score: {score}, rank: {rank})"
                )
                return rank

        logger.debug(f"No ranking found for journal: '{journal_name}'")
        return None

    def find_ranking_with_details(
        self,
        journal_name: str,
        threshold: int = 85
    ) -> Optional[Dict[str, any]]:
        """
        Find ranking with match details.

        Args:
            journal_name: Journal name or abbreviation
            threshold: Minimum fuzzy match score

        Returns:
            Dictionary with rank, matched_name, confidence, or None
        """
        if not journal_name:
            return None

        journal_name = journal_name.strip()

        # Try exact match on journal names
        if journal_name in self.journals:
            return {
                'rank': self.journals[journal_name].get('rank'),
                'matched_name': journal_name,
                'abbreviation': self.journals[journal_name].get('abbreviation', ''),
                'confidence': 100,
                'match_type': 'exact'
            }

        # Try exact match on aliases
        if journal_name in self.aliases:
            full_name = self.aliases[journal_name]
            journal_info = self.journals.get(full_name, {})
            return {
                'rank': journal_info.get('rank'),
                'matched_name': full_name,
                'abbreviation': journal_info.get('abbreviation', ''),
                'confidence': 100,
                'match_type': 'alias'
            }

        # Try fuzzy matching
        normalized = self._normalize_name(journal_name)
        journal_keys = list(self.journals.keys())

        if journal_keys:
            result = process.extractOne(
                normalized,
                [self._normalize_name(k) for k in journal_keys],
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold
            )

            if result:
                _, score, idx = result
                matched_key = journal_keys[idx]
                journal_info = self.journals[matched_key]
                return {
                    'rank': journal_info.get('rank'),
                    'matched_name': matched_key,
                    'abbreviation': journal_info.get('abbreviation', ''),
                    'confidence': score,
                    'match_type': 'fuzzy'
                }

        return None

    def add_journal(
        self,
        journal_name: str,
        rank: str,
        abbreviation: Optional[str] = None
    ) -> bool:
        """
        Add a new journal to the mapping.

        Args:
            journal_name: Full journal name
            rank: Ranking (A*, A, B, C, Q1-Q4, etc.)
            abbreviation: Journal abbreviation

        Returns:
            True if added successfully
        """
        try:
            self.journals[journal_name] = {
                'rank': rank
            }

            if abbreviation:
                self.journals[journal_name]['abbreviation'] = abbreviation
                self.aliases[abbreviation] = journal_name

            logger.info(f"Added journal: {journal_name} ({rank})")
            return True

        except Exception as e:
            logger.error(f"Error adding journal: {e}")
            return False

    def _normalize_name(self, name: str) -> str:
        """
        Normalize journal name for better matching.

        Args:
            name: Raw journal name

        Returns:
            Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()

        # Remove common words
        remove_words = ['the', 'journal', 'of', 'transactions', 'on', 'ieee', 'acm']
        words = normalized.split()
        words = [w for w in words if w not in remove_words]
        normalized = ' '.join(words)

        # Remove punctuation
        for char in '.,;:-/()[]{}':
            normalized = normalized.replace(char, ' ')

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded journals."""
        rank_counts = {}

        for journal_info in self.journals.values():
            rank = journal_info.get('rank', 'Unknown')
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        return {
            'total': len(self.journals),
            'aliases': len(self.aliases),
            'by_rank': rank_counts
        }


def get_journal_ranking(journal_name: str) -> Optional[str]:
    """
    Convenience function to get journal ranking.

    Args:
        journal_name: Journal name or abbreviation

    Returns:
        Ranking or None
    """
    mapper = JournalRankingMapper()
    return mapper.find_ranking(journal_name)
