"""
Interactive ranking resolver for unknown venues.
"""

import logging
from typing import Optional, Dict, List

from rankings.journal_mapper import JournalRankingMapper
from scraper.core_rankings import CoreRankingsFetcher

logger = logging.getLogger(__name__)


class RankingResolver:
    """Interactive resolver for venue rankings."""

    def __init__(
        self,
        core_fetcher: Optional[CoreRankingsFetcher] = None,
        journal_mapper: Optional[JournalRankingMapper] = None
    ):
        """
        Initialize ranking resolver.

        Args:
            core_fetcher: CORE rankings fetcher instance
            journal_mapper: Journal ranking mapper instance
        """
        self.core_fetcher = core_fetcher or CoreRankingsFetcher()
        self.journal_mapper = journal_mapper or JournalRankingMapper()

        # Ensure CORE rankings are loaded
        if not self.core_fetcher.rankings:
            self.core_fetcher.load_rankings()

    def resolve_ranking(
        self,
        venue: str,
        interactive: bool = True,
        auto_save: bool = True
    ) -> Optional[str]:
        """
        Resolve ranking for a venue using multiple sources.

        Args:
            venue: Venue name
            interactive: Whether to prompt user for unknown venues
            auto_save: Whether to automatically save new rankings

        Returns:
            Ranking or None
        """
        if not venue:
            return None

        # Try CORE rankings first (for conferences)
        core_rank = self.core_fetcher.find_ranking(venue)
        if core_rank:
            logger.debug(f"Found CORE ranking for '{venue}': {core_rank}")
            return core_rank

        # Try journal mappings (for journals)
        journal_rank = self.journal_mapper.find_ranking(venue)
        if journal_rank:
            logger.debug(f"Found journal ranking for '{venue}': {journal_rank}")
            return journal_rank

        # If not found and interactive mode enabled, ask user
        if interactive:
            return self._interactive_resolve(venue, auto_save)

        logger.debug(f"No ranking found for '{venue}'")
        return None

    def resolve_batch(
        self,
        venues: List[str],
        interactive: bool = True,
        auto_save: bool = True
    ) -> Dict[str, Optional[str]]:
        """
        Resolve rankings for multiple venues.

        Args:
            venues: List of venue names
            interactive: Whether to prompt user for unknown venues
            auto_save: Whether to automatically save new rankings

        Returns:
            Dictionary mapping venue names to rankings
        """
        rankings = {}
        unknown_venues = []

        # First pass: resolve known venues
        for venue in venues:
            ranking = self.resolve_ranking(venue, interactive=False)
            rankings[venue] = ranking

            if ranking is None and venue:
                unknown_venues.append(venue)

        # Second pass: interactively resolve unknown venues
        if interactive and unknown_venues:
            logger.info(f"\nFound {len(unknown_venues)} unknown venues")

            for venue in unknown_venues:
                ranking = self._interactive_resolve(venue, auto_save)
                rankings[venue] = ranking

        return rankings

    def _interactive_resolve(self, venue: str, auto_save: bool = True) -> Optional[str]:
        """
        Interactively ask user for venue ranking.

        Args:
            venue: Venue name
            auto_save: Whether to save the response

        Returns:
            Ranking or None
        """
        print(f"\n{'='*70}")
        print(f"Unknown venue: {venue}")
        print(f"{'='*70}")
        print("Please enter the ranking for this venue:")
        print("  - Conference: A*, A, B, C, or 'skip'")
        print("  - Journal: A*, A, B, C, Q1, Q2, Q3, Q4, or 'skip'")
        print("  - Type 'skip' to skip this venue")
        print("  - Type 'unknown' to mark as unknown")

        while True:
            response = input("\nRanking: ").strip()

            if not response:
                continue

            response_lower = response.lower()

            # Handle skip
            if response_lower == 'skip':
                logger.info(f"Skipped venue: {venue}")
                return None

            # Handle unknown
            if response_lower == 'unknown':
                logger.info(f"Marked as unknown: {venue}")
                return "Unknown"

            # Validate ranking format
            valid_rankings = ['A*', 'A', 'B', 'C', 'Q1', 'Q2', 'Q3', 'Q4']
            if response.upper() in valid_rankings:
                ranking = response.upper()

                # Ask if it's a journal (to save to journal mappings)
                is_journal = input("Is this a journal? (y/n): ").strip().lower() == 'y'

                if auto_save and is_journal:
                    # Ask for abbreviation
                    abbrev = input("Journal abbreviation (optional, press Enter to skip): ").strip()
                    abbrev = abbrev if abbrev else None

                    # Save to journal mappings
                    self.journal_mapper.add_journal(venue, ranking, abbrev)
                    self.journal_mapper.save_mappings()
                    logger.info(f"Saved journal ranking: {venue} = {ranking}")

                return ranking

            print(f"Invalid ranking: {response}. Please enter one of: {', '.join(valid_rankings)}, skip, or unknown")

    def get_ranking_stats(self) -> Dict[str, any]:
        """Get statistics about available rankings."""
        core_stats = self.core_fetcher.get_stats()
        journal_stats = self.journal_mapper.get_stats()

        return {
            'core_conferences': core_stats,
            'journals': journal_stats
        }

    def print_stats(self) -> None:
        """Print statistics about available rankings."""
        stats = self.get_ranking_stats()

        print("\n" + "="*70)
        print("RANKING STATISTICS")
        print("="*70)

        print(f"\nCORE Conference Rankings:")
        print(f"  Total conferences: {stats['core_conferences']['total']}")
        if stats['core_conferences']['by_rank']:
            for rank, count in sorted(stats['core_conferences']['by_rank'].items()):
                print(f"    {rank}: {count}")

        print(f"\nJournal Rankings:")
        print(f"  Total journals: {stats['journals']['total']}")
        print(f"  Aliases: {stats['journals']['aliases']}")
        if stats['journals']['by_rank']:
            for rank, count in sorted(stats['journals']['by_rank'].items()):
                print(f"    {rank}: {count}")

        print("="*70 + "\n")


def resolve_venue_ranking(
    venue: str,
    interactive: bool = True
) -> Optional[str]:
    """
    Convenience function to resolve a single venue ranking.

    Args:
        venue: Venue name
        interactive: Whether to prompt user for unknown venues

    Returns:
        Ranking or None
    """
    resolver = RankingResolver()
    return resolver.resolve_ranking(venue, interactive=interactive)
