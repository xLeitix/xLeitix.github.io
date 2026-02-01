# Google Scholar Statistics Scraper

A Python tool to scrape Google Scholar profiles and export publication statistics to CSV with automatic conference (CORE) and journal rankings.

## Features

- Scrapes publication data from Google Scholar profiles
- Exports to CSV with fields: title, authors, venue, year, citations, ranking
- Automatically fetches CORE conference rankings
- Supports pre-configured journal ranking mappings
- Interactive prompts for unknown venues
- Rate limiting to avoid getting blocked
- Checkpoint/resume functionality for large profiles
- Anti-detection measures using Selenium

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed (for Selenium WebDriver)

### Setup

1. **Clone or download this repository**

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Verify installation**

```bash
python src/main.py --help
```

## Usage

### Basic Usage

Scrape a Google Scholar profile and export to CSV:

```bash
python src/main.py --url "https://scholar.google.com/citations?user=USER_ID"
```

This will:
1. Open a visible browser window (allows manual CAPTCHA solving if needed)
2. Scrape all papers from the profile
3. Fetch CORE conference rankings automatically
4. Prompt you interactively for journal rankings of unknown venues
5. Export results to `scholar_stats.csv`

### Advanced Usage

**Specify output file:**

```bash
python src/main.py --url "https://scholar.google.com/..." --output my_papers.csv
```

**Run in headless mode (faster, but can't solve CAPTCHAs manually):**

```bash
python src/main.py --url "https://scholar.google.com/..." --headless
```

**Extract detailed information from paper pages (more accurate but slower):**

```bash
python src/main.py --url "https://scholar.google.com/..." --extract-details
```

**Skip interactive prompts (leaves unknown venues blank):**

```bash
python src/main.py --url "https://scholar.google.com/..." --no-interactive
```

**Force refresh CORE rankings from web:**

```bash
python src/main.py --url "https://scholar.google.com/..." --refresh-core
```

**Enable verbose logging:**

```bash
python src/main.py --url "https://scholar.google.com/..." --verbose
```

### Full Example

```bash
python src/main.py \
    --url "https://scholar.google.com/citations?user=ABC123XYZ" \
    --output results.csv \
    --extract-details \
    --verbose
```

## Configuration

### Rate Limiting

Edit `config/scraper_config.yaml` to adjust rate limiting parameters:

```yaml
rate_limiting:
  min_delay: 3.0              # Minimum seconds between requests
  max_delay: 6.0              # Maximum seconds between requests
  page_delay: 4.0             # Delay after each page load
  error_delay: 15.0           # Delay after errors
  max_retries: 3              # Retry attempts
  requests_per_minute: 8      # Max requests per minute
```

**Important:** Start with conservative delays (3-6 seconds) to avoid getting blocked. You can adjust based on your experience.

### Journal Rankings

Pre-configure journal rankings in `data/journal_rankings.json`:

```json
{
  "journals": {
    "IEEE Transactions on Software Engineering": {
      "rank": "A*",
      "abbreviation": "TSE"
    }
  },
  "aliases": {
    "TSE": "IEEE Transactions on Software Engineering"
  }
}
```

The script will automatically add new journals when you provide rankings interactively.

## Output Format

The CSV file contains the following columns:

- **title**: Paper title
- **authors**: Semicolon-separated list of authors
- **venue**: Conference or journal name
- **year**: Publication year
- **citations**: Number of citations
- **ranking**: CORE ranking (A*, A, B, C) or journal ranking (A*, A, B, C, Q1-Q4)

Example:

```csv
title,authors,venue,year,citations,ranking
"Deep Learning for NLP",John Doe; Jane Smith,ACL,2020,125,A*
"Survey of Machine Learning",Jane Smith,IEEE TSE,2019,230,A*
```

## Troubleshooting

### CAPTCHA Detection

If Google Scholar shows a CAPTCHA:

1. **Run in visible mode** (without `--headless`)
2. Solve the CAPTCHA manually in the browser window
3. Press Enter in the terminal to continue
4. The script will save a checkpoint and can resume if interrupted

### Getting Blocked

If you get blocked:

1. **Wait 24-48 hours** before trying again
2. **Increase delays** in `config/scraper_config.yaml`
3. **Run during off-peak hours** (late night/early morning)
4. **Process in smaller batches** if you have many papers

### Browser Driver Issues

If you get WebDriver errors:

```bash
# The undetected-chromedriver library should handle this automatically
# If issues persist, try updating:
pip install --upgrade undetected-chromedriver
```

### Resuming After Interruption

If the script is interrupted (CAPTCHA, error, Ctrl+C):

1. A checkpoint file `checkpoint.json` is automatically saved
2. Simply run the same command again
3. The script will resume from where it left off
4. The checkpoint is automatically deleted upon successful completion

## Tips for Successful Scraping

1. **Start with visible mode**: Run without `--headless` first to monitor for CAPTCHAs
2. **Be patient**: Conservative rate limiting is key to avoiding blocks
3. **Small batches**: For profiles with 500+ papers, consider breaking into multiple sessions
4. **Off-peak hours**: Run during late night or early morning to reduce detection risk
5. **Verify data**: Always manually check the first 10-20 entries for accuracy

## Project Structure

```
scholar_profile_parser/
├── src/
│   ├── main.py                      # CLI entry point
│   ├── scraper/
│   │   ├── selenium_config.py       # Anti-detection setup
│   │   ├── scholar_scraper.py       # Main scraper
│   │   ├── core_rankings.py         # CORE rankings fetcher
│   │   └── rate_limiter.py          # Rate limiting
│   ├── parsers/
│   │   └── profile_parser.py        # HTML parser
│   ├── rankings/
│   │   ├── journal_mapper.py        # Journal rankings
│   │   └── ranking_resolver.py      # Interactive resolver
│   └── exporters/
│       └── csv_exporter.py          # CSV export
├── data/
│   ├── journal_rankings.json        # Journal mappings
│   └── core_rankings_cache.json     # Cached CORE rankings
├── config/
│   ├── scraper_config.yaml          # Configuration
│   └── user_agents.txt              # User agent rotation
├── requirements.txt
└── README.md
```

## Ethical Considerations

- **Respect robots.txt**: Google Scholar blocks automated robots, but manual browsing with conservative rate limits is generally acceptable
- **Personal use**: This tool is intended for personal research use, not commercial scraping
- **Rate limiting**: Always use conservative delays to avoid overloading servers
- **Data attribution**: Cite Google Scholar as your data source in any publications

## Logging

All scraping activity is logged to `scraper.log` in the current directory. Check this file if you encounter errors.

## Additional Commands

**Show version:**

```bash
python src/main.py version
```

**Show available ranking statistics:**

```bash
python src/main.py show-rankings

# Or refresh from web:
python src/main.py show-rankings --refresh
```

## Support

If you encounter issues:

1. Check `scraper.log` for detailed error messages
2. Verify your profile URL is correct
3. Try running with `--verbose` for more information
4. Ensure Chrome browser is installed and up to date

## License

This tool is provided as-is for educational and research purposes.

## Acknowledgments

- CORE Conference Rankings: https://portal.core.edu.au/
- Google Scholar: https://scholar.google.com/
