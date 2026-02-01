#!/usr/bin/env python3
"""Generate tpms.txt with downloadable PDF links for papers in scholar_full_profile.csv.

Phase 1: arXiv direct links + Semantic Scholar API lookups
Phase 2: Google Scholar fallback for remaining papers (uses Selenium)
"""

import csv
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Add src/ to path so we can import the scraper infrastructure
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bs4 import BeautifulSoup
from scraper.scholar_scraper import ScholarScraper
from scraper.rate_limiter import load_rate_limiter_from_config

# Default Google Scholar profile URL
SCHOLAR_PROFILE_URL = "https://scholar.google.com/citations?user=wZ9f8CAAAAAJ&hl=en"

CHECKPOINT_FILE = "tpms_checkpoint.json"

logger = logging.getLogger(__name__)


def parse_csv(path):
    """Parse all entries from the CSV, skipping non-paper rows."""
    papers = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            venue = row.get("venue", "").strip()
            year = row.get("year", "").strip()
            # Skip entries with no title or no year
            if not title or not year or year == "":
                continue
            # Skip obvious non-papers (committee listings, etc.)
            try:
                float(year)
            except ValueError:
                continue
            papers.append({"title": title, "venue": venue, "year": year})
    return papers


def extract_arxiv_id(venue):
    """Extract arXiv ID from venue string if present."""
    m = re.search(r"arXiv[:\s]*(\d{4}\.\d{4,5})", venue)
    if m:
        return m.group(1)
    return None


def arxiv_pdf_url(arxiv_id):
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def semantic_scholar_lookup(title, max_retries=5):
    """Query Semantic Scholar for a paper's open access PDF URL with retry on 429."""
    encoded = urllib.parse.quote(title)
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded}&limit=1&fields=openAccessPdf,title"

    for attempt in range(max_retries):
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ScholarProfileParser/1.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 3 * (2 ** attempt)  # 3, 6, 12, 24, 48 seconds
                print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            print(f"  HTTP error: {e}")
            return None
        except Exception as e:
            print(f"  API error: {e}")
            return None
    else:
        print(f"  Exhausted retries")
        return None

    results = data.get("data", [])
    if not results:
        return None

    paper = results[0]
    # Basic title match check
    returned_title = paper.get("title", "")
    if not fuzzy_match(title, returned_title):
        print(f"  Title mismatch: '{returned_title[:60]}...'")
        return None

    oa = paper.get("openAccessPdf")
    if oa and oa.get("url"):
        return oa["url"]
    return None


def normalize_title(s):
    """Normalize a title for fuzzy comparison."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return " ".join(s.split())


def fuzzy_match(query, result):
    """Check if two titles are similar enough (case-insensitive, ignoring punctuation)."""
    nq = normalize_title(query)
    nr = normalize_title(result)
    if not nq or not nr:
        return False
    # Check if one contains most of the other
    q_words = set(nq.split())
    r_words = set(nr.split())
    if not q_words:
        return False
    overlap = len(q_words & r_words) / len(q_words)
    return overlap >= 0.7


def load_checkpoint():
    """Load checkpoint from file if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                data = json.load(f)
            print(f"Loaded checkpoint: {len(data.get('pdf_map', {}))} URLs found so far")
            return data
        except Exception as e:
            print(f"Warning: failed to load checkpoint: {e}")
    return None


def save_checkpoint(pdf_map, phase, gs_progress=None):
    """Save current progress to checkpoint file."""
    data = {
        "pdf_map": pdf_map,
        "phase": phase,
        "gs_progress": gs_progress or [],
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def delete_checkpoint():
    """Delete checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


def wait_for_captcha_resolution(parser, timeout=300, poll_interval=5):
    """Poll the page until the CAPTCHA is resolved or timeout is reached.

    The browser window is visible so the user can solve it manually.
    We just poll is_captcha_page() until it returns False.

    Returns True if resolved, False if timed out.
    """
    print("  CAPTCHA detected! Please solve it in the browser window.")
    print(f"  Waiting up to {timeout}s for CAPTCHA to be resolved...")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(poll_interval)
        if not parser.is_captcha_page():
            print("  CAPTCHA resolved — continuing.")
            return True
        elapsed = int(time.time() - start)
        print(f"  Still waiting for CAPTCHA... ({elapsed}s elapsed)")
    print("  CAPTCHA timeout — giving up.")
    return False


def extract_pdf_link_from_detail_page(driver, parser, detail_url, rate_limiter):
    """
    Navigate to a Google Scholar paper detail page and extract the PDF/publisher link.

    The detail page has a div#gsc_oci_title_gg containing child divs with <a> tags
    linking to PDF or publisher versions.

    Args:
        driver: Selenium WebDriver
        parser: ScholarProfileParser instance
        detail_url: URL of the paper detail page
        rate_limiter: RateLimiter instance

    Returns:
        URL string or None
    """
    rate_limiter.wait_if_needed()

    driver.get(detail_url)
    rate_limiter.random_delay()

    # Check for CAPTCHA
    if parser.is_captcha_page():
        if not wait_for_captcha_resolution(parser):
            return None

    # Wait for detail page to load
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#gsc_oci_title"))
        )
    except TimeoutException:
        return None

    soup = BeautifulSoup(driver.page_source, "lxml")

    # Look for PDF/publisher links in the title section
    title_gg = soup.select_one("div#gsc_oci_title_gg")
    if title_gg:
        link = title_gg.select_one("a")
        if link and link.get("href"):
            return link["href"]

    return None


def google_scholar_fallback(papers, pdf_map, profile_url):
    """
    Phase 2: Use Google Scholar profile to find PDF links for papers
    that Semantic Scholar couldn't resolve.

    Args:
        papers: list of paper dicts from CSV
        pdf_map: dict of title -> url (already found)
        profile_url: Google Scholar profile URL

    Returns:
        Updated pdf_map
    """
    # Identify papers still missing
    missing = [p for p in papers if p["title"] not in pdf_map]
    if not missing:
        print("\nNo missing papers — skipping Google Scholar phase.")
        return pdf_map

    print(f"\n{'='*60}")
    print(f"Phase 2: Google Scholar fallback for {len(missing)} papers")
    print(f"{'='*60}")
    print(f"Profile: {profile_url}")
    print("Browser will open — solve CAPTCHA if prompted.\n")

    # Load checkpoint to see which GS detail pages we already visited
    checkpoint = load_checkpoint()
    gs_done = set()
    if checkpoint and checkpoint.get("gs_progress"):
        gs_done = set(checkpoint["gs_progress"])

    scraper = ScholarScraper(profile_url, headless=False, simple_mode=True)
    try:
        scraper.initialize()
        driver = scraper.driver
        parser = scraper.parser
        rate_limiter = scraper.rate_limiter

        # Navigate to profile and load all papers
        print("Loading profile and all papers...")
        driver.get(profile_url)
        rate_limiter.page_load_delay()

        if parser.is_captcha_page():
            if not wait_for_captcha_resolution(parser):
                print("Could not resolve CAPTCHA — aborting Google Scholar phase.")
                return pdf_map

        if not parser.wait_for_papers_table():
            print("Error: could not load papers table")
            return pdf_map

        # Click "Show more" until all papers are loaded
        profile_papers = scraper._load_all_papers()
        print(f"Loaded {len(profile_papers)} papers from Google Scholar profile")

        # Build normalized title -> detail_link map from profile
        gs_title_map = {}
        for gp in profile_papers:
            gs_norm = normalize_title(gp.get("title", ""))
            if gs_norm and gp.get("detail_link"):
                gs_title_map[gs_norm] = gp["detail_link"]

        # Match missing papers to profile entries
        matched = []
        for paper in missing:
            csv_norm = normalize_title(paper["title"])
            # Try exact normalized match first
            if csv_norm in gs_title_map:
                matched.append((paper["title"], gs_title_map[csv_norm]))
                continue
            # Try fuzzy match
            for gs_norm, detail_link in gs_title_map.items():
                if fuzzy_match(paper["title"], gs_norm):
                    matched.append((paper["title"], detail_link))
                    break

        print(f"Matched {len(matched)}/{len(missing)} missing papers to profile entries")

        unmatched_count = len(missing) - len(matched)
        if unmatched_count > 0:
            print(f"  ({unmatched_count} papers not found on profile)")

        # Visit each matched detail page to extract PDF link
        gs_found = 0
        for idx, (title, detail_link) in enumerate(matched):
            if title in pdf_map:
                continue  # already found
            if title in gs_done:
                continue  # already visited in a previous run

            print(f"  [{idx+1}/{len(matched)}] {title[:65]}...")

            pdf_url = extract_pdf_link_from_detail_page(
                driver, parser, detail_link, rate_limiter
            )

            if pdf_url:
                pdf_map[title] = pdf_url
                gs_found += 1
                print(f"    Found: {pdf_url[:80]}")
            else:
                print(f"    No link found")

            gs_done.add(title)

            # Checkpoint every 10 papers
            if (idx + 1) % 10 == 0:
                save_checkpoint(pdf_map, "google_scholar", list(gs_done))

        print(f"\nGoogle Scholar phase found {gs_found} additional PDFs")
        save_checkpoint(pdf_map, "done", list(gs_done))

    except KeyboardInterrupt:
        print("\nInterrupted — saving checkpoint...")
        save_checkpoint(pdf_map, "google_scholar", list(gs_done))
        raise
    except Exception as e:
        print(f"\nError in Google Scholar phase: {e}")
        save_checkpoint(pdf_map, "google_scholar", list(gs_done))
    finally:
        scraper.cleanup()

    return pdf_map


def main():
    csv_path = "scholar_full_profile.csv"
    output_path = "tpms.txt"

    # Setup basic logging for the scraper modules
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    papers = parse_csv(csv_path)
    print(f"Parsed {len(papers)} papers from {csv_path}")

    # Check for checkpoint to resume from
    checkpoint = load_checkpoint()
    if checkpoint and checkpoint.get("pdf_map"):
        pdf_map = checkpoint["pdf_map"]
        phase = checkpoint.get("phase", "semantic_scholar")
        print(f"Resuming from checkpoint (phase: {phase}, {len(pdf_map)} URLs found)")
    else:
        pdf_map = {}  # title -> url
        phase = "start"

    # ---- Phase 1: arXiv + Semantic Scholar ----
    if phase in ("start", "semantic_scholar"):
        arxiv_count = 0
        api_count = 0

        for i, paper in enumerate(papers):
            title = paper["title"]
            venue = paper["venue"]

            # Skip if already resolved
            if title in pdf_map:
                continue

            print(f"[{i+1}/{len(papers)}] {title[:70]}...")

            # Try arXiv shortcut first
            arxiv_id = extract_arxiv_id(venue)
            if arxiv_id:
                url = arxiv_pdf_url(arxiv_id)
                pdf_map[title] = url
                arxiv_count += 1
                print(f"  arXiv: {url}")
                continue

            # Semantic Scholar lookup
            api_count += 1
            url = semantic_scholar_lookup(title)
            if url:
                pdf_map[title] = url
                print(f"  Found: {url[:80]}...")
            else:
                print(f"  No PDF found")

            # Rate limiting: stay under 100 req / 5 min
            time.sleep(3.5)

            # Checkpoint every 25 papers
            if (i + 1) % 25 == 0:
                save_checkpoint(pdf_map, "semantic_scholar")

        save_checkpoint(pdf_map, "semantic_scholar_done")
        print(f"\nPhase 1 complete: {len(pdf_map)} PDFs found "
              f"(arXiv: {arxiv_count}, Semantic Scholar API: {api_count})")

    # ---- Phase 2: Google Scholar fallback ----
    profile_url = os.environ.get("SCHOLAR_PROFILE_URL", SCHOLAR_PROFILE_URL)
    pdf_map = google_scholar_fallback(papers, pdf_map, profile_url)

    # ---- Write results ----
    # Build ordered URL list matching paper order in CSV
    pdf_urls = []
    for paper in papers:
        url = pdf_map.get(paper["title"])
        if url:
            pdf_urls.append(url)

    with open(output_path, "w") as f:
        for url in pdf_urls:
            f.write(url + "\n")

    found_count = len(pdf_urls)
    missing_titles = [p["title"] for p in papers if p["title"] not in pdf_map]

    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Total papers: {len(papers)}")
    print(f"PDFs found: {found_count}")
    print(f"Missing: {len(missing_titles)}")
    print(f"Output: {output_path} ({len(pdf_urls)} URLs)")

    if missing_titles:
        print(f"\nPapers still without PDF links:")
        for t in missing_titles:
            print(f"  - {t[:80]}")

    # Clean up checkpoint only if all papers resolved
    if not missing_titles:
        delete_checkpoint()
    else:
        # Save checkpoint so next run can skip Phase 1 and resume GS
        save_checkpoint(pdf_map, "semantic_scholar_done")
        print(f"\nCheckpoint saved — run again to resume Google Scholar phase.")


if __name__ == "__main__":
    main()
