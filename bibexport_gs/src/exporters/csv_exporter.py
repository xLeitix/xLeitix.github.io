"""
CSV exporter for Google Scholar statistics.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class CSVExporter:
    """Exporter for Google Scholar statistics to CSV format."""

    REQUIRED_FIELDS = ['title', 'authors', 'venue', 'year', 'citations', 'ranking']

    def __init__(self, output_path: str):
        """
        Initialize CSV exporter.

        Args:
            output_path: Path to output CSV file
        """
        self.output_path = Path(output_path)

    def export(
        self,
        papers: List[Dict[str, Any]],
        include_extra_fields: bool = False
    ) -> bool:
        """
        Export papers to CSV file.

        Args:
            papers: List of paper dictionaries
            include_extra_fields: Whether to include extra fields beyond required

        Returns:
            True if export successful
        """
        if not papers:
            logger.warning("No papers to export")
            return False

        try:
            # Prepare data for export
            export_data = self._prepare_data(papers, include_extra_fields)

            # Create parent directory if needed
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Export using pandas for better handling
            df = pd.DataFrame(export_data)

            # Reorder columns to match required fields first
            columns = self.REQUIRED_FIELDS.copy()
            if include_extra_fields:
                extra_cols = [col for col in df.columns if col not in columns]
                columns.extend(extra_cols)
                df = df[columns]

            # Export to CSV with UTF-8 BOM for Excel compatibility
            df.to_csv(
                self.output_path,
                index=False,
                encoding='utf-8-sig',  # UTF-8 with BOM
                quoting=csv.QUOTE_MINIMAL
            )

            logger.info(f"Exported {len(papers)} papers to {self.output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False

    def _prepare_data(
        self,
        papers: List[Dict[str, Any]],
        include_extra: bool
    ) -> List[Dict[str, Any]]:
        """
        Prepare paper data for CSV export.

        Args:
            papers: List of paper dictionaries
            include_extra: Whether to include extra fields

        Returns:
            List of prepared paper dictionaries
        """
        export_data = []

        for paper in papers:
            # Extract required fields
            row = {
                'title': self._sanitize_field(paper.get('title', '')),
                'authors': self._format_authors(paper.get('authors', [])),
                'venue': self._sanitize_field(paper.get('venue', '')),
                'year': paper.get('year', ''),
                'citations': paper.get('citations', 0),
                'ranking': paper.get('ranking', '')
            }

            # Add extra fields if requested
            if include_extra:
                extra_fields = ['detail_link', 'row_index', 'match_confidence']
                for field in extra_fields:
                    if field in paper:
                        row[field] = paper[field]

            export_data.append(row)

        return export_data

    def _format_authors(self, authors) -> str:
        """
        Format authors field for CSV export.

        Args:
            authors: Authors as string or list

        Returns:
            Formatted authors string
        """
        if not authors:
            return ""

        # If already a string, return as is
        if isinstance(authors, str):
            return self._sanitize_field(authors)

        # If list, join with semicolons
        if isinstance(authors, list):
            return "; ".join(self._sanitize_field(str(a)) for a in authors)

        return self._sanitize_field(str(authors))

    def _sanitize_field(self, field: Any) -> str:
        """
        Sanitize field value for CSV export.

        Args:
            field: Field value

        Returns:
            Sanitized string
        """
        if field is None:
            return ""

        # Convert to string
        field_str = str(field).strip()

        # Remove problematic characters that might break CSV
        # Keep most unicode characters for international names
        field_str = field_str.replace('\n', ' ').replace('\r', ' ')
        field_str = field_str.replace('\t', ' ')

        # Remove extra whitespace
        field_str = ' '.join(field_str.split())

        return field_str

    def export_summary_stats(self, papers: List[Dict[str, Any]]) -> str:
        """
        Generate summary statistics about exported papers.

        Args:
            papers: List of paper dictionaries

        Returns:
            Summary statistics as string
        """
        if not papers:
            return "No papers to summarize"

        total = len(papers)

        # Count by ranking
        ranking_counts = {}
        unknown_count = 0
        for paper in papers:
            ranking = paper.get('ranking', '')
            if not ranking or ranking == 'Unknown':
                unknown_count += 1
            else:
                ranking_counts[ranking] = ranking_counts.get(ranking, 0) + 1

        # Count citations stats
        citations = [p.get('citations', 0) for p in papers]
        total_citations = sum(citations)
        avg_citations = total_citations / total if total > 0 else 0
        max_citations = max(citations) if citations else 0

        # Count by year
        years = [p.get('year') for p in papers if p.get('year')]
        year_range = f"{min(years)}-{max(years)}" if years else "N/A"

        summary = f"""
Export Summary:
{'='*70}
Total papers: {total}
Year range: {year_range}

Citations:
  Total: {total_citations}
  Average: {avg_citations:.1f}
  Maximum: {max_citations}

Rankings:
"""
        for ranking in sorted(ranking_counts.keys()):
            count = ranking_counts[ranking]
            percentage = (count / total) * 100
            summary += f"  {ranking}: {count} ({percentage:.1f}%)\n"

        if unknown_count > 0:
            percentage = (unknown_count / total) * 100
            summary += f"  Unknown/Not ranked: {unknown_count} ({percentage:.1f}%)\n"

        summary += "="*70

        return summary


def export_to_csv(
    papers: List[Dict[str, Any]],
    output_path: str,
    include_extra_fields: bool = False
) -> bool:
    """
    Convenience function to export papers to CSV.

    Args:
        papers: List of paper dictionaries
        output_path: Path to output CSV file
        include_extra_fields: Whether to include extra fields

    Returns:
        True if export successful
    """
    exporter = CSVExporter(output_path)
    return exporter.export(papers, include_extra_fields=include_extra_fields)
