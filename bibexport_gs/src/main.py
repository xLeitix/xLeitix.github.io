#!/usr/bin/env python3
"""
Google Scholar Profile Statistics Scraper

Command-line tool to scrape Google Scholar profiles and export statistics to CSV
with automatic conference (CORE) and journal rankings.
"""

import sys
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import click

from scraper.scholar_scraper import ScholarScraper
from scraper.core_rankings import CoreRankingsFetcher
from rankings.journal_mapper import JournalRankingMapper
from rankings.ranking_resolver import RankingResolver
from exporters.csv_exporter import CSVExporter


# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


@click.command()
@click.option(
    '--url',
    required=True,
    help='Google Scholar profile URL'
)
@click.option(
    '--output',
    default='scholar_stats.csv',
    help='Output CSV file path (default: scholar_stats.csv)'
)
@click.option(
    '--headless',
    is_flag=True,
    default=False,
    help='Run browser in headless mode (default: visible)'
)
@click.option(
    '--extract-details',
    is_flag=True,
    default=False,
    help='Extract detailed information from paper pages (slower but more accurate)'
)
@click.option(
    '--refresh-core',
    is_flag=True,
    default=False,
    help='Force refresh CORE conference rankings from web'
)
@click.option(
    '--no-interactive',
    is_flag=True,
    default=False,
    help='Skip interactive prompts for unknown venues'
)
@click.option(
    '--verbose',
    is_flag=True,
    default=False,
    help='Enable verbose logging'
)
@click.option(
    '--limit',
    type=int,
    default=None,
    help='Limit number of papers to scrape (for testing)'
)
@click.option(
    '--simple',
    is_flag=True,
    default=False,
    help='Use simple Selenium (for testing when undetected-chromedriver has issues)'
)
def main(
    url: str,
    output: str,
    headless: bool,
    extract_details: bool,
    refresh_core: bool,
    no_interactive: bool,
    verbose: bool,
    limit: int,
    simple: bool
):
    """
    Scrape Google Scholar profile and export statistics to CSV.

    Example usage:

        python src/main.py --url "https://scholar.google.com/citations?user=USER_ID"

        python src/main.py --url "https://scholar.google.com/citations?user=USER_ID" \\
                           --output results.csv --headless --extract-details
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        click.echo("\n" + "="*70)
        click.echo("Google Scholar Profile Statistics Scraper")
        click.echo("="*70 + "\n")

        # Step 1: Initialize components
        click.echo("Initializing components...")

        core_fetcher = CoreRankingsFetcher()
        journal_mapper = JournalRankingMapper()
        resolver = RankingResolver(core_fetcher, journal_mapper)

        # Step 2: Load CORE rankings
        click.echo("\nLoading CORE conference rankings...")
        if not core_fetcher.load_rankings(force_refresh=refresh_core):
            click.echo("Warning: Failed to load CORE rankings. Conference rankings may be incomplete.")
        else:
            stats = core_fetcher.get_stats()
            click.echo(f"  Loaded {stats['total']} conferences")

        # Step 3: Load journal mappings
        journal_stats = journal_mapper.get_stats()
        click.echo(f"\nLoaded journal mappings:")
        click.echo(f"  {journal_stats['total']} journals, {journal_stats['aliases']} aliases")

        # Step 4: Scrape profile
        click.echo(f"\nScraping profile: {url}")
        click.echo(f"Mode: {'headless' if headless else 'visible browser'}")
        click.echo(f"Extract details: {'yes' if extract_details else 'no'}")

        if not headless:
            click.echo("\nNote: Running in visible mode. You can manually solve CAPTCHAs if needed.")

        with ScholarScraper(url, headless=headless, simple_mode=simple) as scraper:
            papers = scraper.scrape_profile(extract_details=extract_details)

            # Apply limit if specified (for testing)
            if limit and limit > 0:
                papers = papers[:limit]
                click.echo(f"Limited to first {limit} papers for testing")

        if not papers:
            click.echo("\nError: No papers found. Check the profile URL and try again.")
            sys.exit(1)

        click.echo(f"\nSuccessfully scraped {len(papers)} papers")

        # Step 5: Resolve rankings
        click.echo("\nResolving venue rankings...")

        venues = [p['venue'] for p in papers if p.get('venue')]
        unique_venues = list(set(venues))

        click.echo(f"Found {len(unique_venues)} unique venues")

        interactive = not no_interactive
        venue_rankings = resolver.resolve_batch(
            unique_venues,
            interactive=interactive,
            auto_save=True
        )

        # Assign rankings to papers
        for paper in papers:
            venue = paper.get('venue', '')
            paper['ranking'] = venue_rankings.get(venue, '')

        # Count resolved rankings
        ranked_count = sum(1 for p in papers if p.get('ranking'))
        click.echo(f"\nResolved rankings for {ranked_count}/{len(papers)} papers")

        # Step 6: Export to CSV
        click.echo(f"\nExporting to CSV: {output}")

        exporter = CSVExporter(output)
        if not exporter.export(papers):
            click.echo("\nError: Failed to export CSV")
            sys.exit(1)

        # Step 7: Print summary
        click.echo("\n" + exporter.export_summary_stats(papers))

        click.echo(f"\n✓ Success! Statistics saved to: {output}\n")

    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user. Progress saved to checkpoint if applicable.")
        sys.exit(130)

    except Exception as e:
        logger.exception("Fatal error")
        click.echo(f"\nError: {e}")
        click.echo("Check scraper.log for details")
        sys.exit(1)


@click.group()
def cli():
    """Google Scholar Statistics Scraper CLI"""
    pass


@cli.command()
def version():
    """Show version information"""
    click.echo("Google Scholar Statistics Scraper v1.0.0")


@cli.command()
@click.option('--refresh', is_flag=True, help='Refresh CORE rankings from web')
def show_rankings(refresh: bool):
    """Show available ranking statistics"""
    setup_logging(verbose=False)

    core_fetcher = CoreRankingsFetcher()
    journal_mapper = JournalRankingMapper()
    resolver = RankingResolver(core_fetcher, journal_mapper)

    if refresh:
        click.echo("Refreshing CORE rankings from web...")
        core_fetcher.load_rankings(force_refresh=True)
    else:
        core_fetcher.load_rankings()

    resolver.print_stats()


if __name__ == '__main__':
    # Support both direct main() call and CLI commands
    if len(sys.argv) > 1 and sys.argv[1] in ['version', 'show-rankings']:
        cli()
    else:
        main()
