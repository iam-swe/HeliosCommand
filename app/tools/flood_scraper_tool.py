"""Firecrawl-based web scraping tool for real-time flood NEWS.

STRICTLY scrapes only news websites for current flood information.
Rejects non-news sources, historical content, and social media.
"""

import os
import re
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.tools import tool

# ── Allowlist of news domains ──────────────────────────────────────
# Only pages from these domains (or their subdomains) will be scraped.
NEWS_DOMAINS = {
    # Indian news
    "ndtv.com", "thehindu.com", "timesofindia.indiatimes.com",
    "indiatimes.com", "indianexpress.com", "indiatoday.in",
    "hindustantimes.com", "news18.com", "livemint.com",
    "deccanherald.com", "deccanchronicle.com", "thequint.com",
    "scroll.in", "firstpost.com", "theprint.in", "telegraphindia.com",
    "newindianexpress.com", "oneindia.com", "zeenews.com",
    # News agencies
    "aninews.in", "ptinews.com",
    # Weather / Met
    "weather.com", "accuweather.com", "mausam.imd.gov.in", "imd.gov.in",
    # International
    "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com",
    "aljazeera.com", "cnn.com", "theguardian.com",
    # Flood-specific government
    "ndma.gov.in", "cwc.gov.in",
}


def _is_news_domain(url: str) -> bool:
    """Check if a URL belongs to one of the allowed news domains."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().lstrip("www.")
        # Check exact match or subdomain match
        for domain in NEWS_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


def _looks_like_current_news(text: str) -> bool:
    """Quick heuristic: does the text look like a current news article?
    
    Checks for recent date patterns and news-like content.
    Rejects pages that look historical or archival.
    """
    text_lower = text[:3000].lower()  # Only check the top portion

    # Reject obvious historical / archival content
    historical_signals = [
        "historical flood data", "flood history", "past floods",
        "annual report", "research paper", "wikipedia",
        "archived", "case study", "published in 20",
    ]
    for signal in historical_signals:
        if signal in text_lower:
            return False

    # Look for current date indicators
    now = datetime.now()
    current_year = str(now.year)
    current_month = now.strftime("%B").lower()  # e.g. "february"
    short_month = now.strftime("%b").lower()    # e.g. "feb"

    # Accept if the text mentions the current year
    if current_year in text_lower:
        return True

    # Accept if common news patterns are present
    news_signals = [
        "updated", "breaking", "latest", "live updates",
        "reported", "officials said", "according to",
        "rescue", "evacuated", "alert issued",
        current_month, short_month,
    ]
    return any(signal in text_lower for signal in news_signals)


@tool
def firecrawl_flood_search(query: str, num_results: int = 3) -> str:
    """Search the web for CURRENT flood news articles and return their content.

    IMPORTANT: This tool ONLY scrapes reputable news websites.
    It will reject non-news pages, social media, blogs, and historical content.

    Args:
        query: The search query about current floods (include 'today' or the year).
        num_results: Number of results to retrieve (default: 3).

    Returns:
        Structured content from news articles with title, source URL,
        and extracted text. Returns an error message if no current
        news is found.
    """
    from firecrawl import Firecrawl

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("     ❌  [FIRECRAWL] FIRECRAWL_API_KEY not set — cannot search")
        return "ERROR: FIRECRAWL_API_KEY not set in environment. Cannot perform web search."

    app = Firecrawl(api_key=api_key)

    print(f"     🔎  [FIRECRAWL] Searching (news only): \"{query}\" …")

    try:
        search_result = app.search(query=query, limit=num_results)
    except Exception as e:
        print(f"     ❌  [FIRECRAWL] Search failed: {e}")
        return f"Search failed: {str(e)}"

    if not search_result or not getattr(search_result, "web", None):
        print("     ⚠️  [FIRECRAWL] No results returned")
        return "No relevant news sources found for this query."

    total = len(search_result.web)
    print(f"     📄  [FIRECRAWL] Got {total} results — filtering for news sites …")

    contents: List[str] = []

    for i, item in enumerate(search_result.web, 1):
        url = item.url

        # ── Filter 1: Only allow news domains ──
        if not _is_news_domain(url):
            print(f"     🚫  [FIRECRAWL] [{i}/{total}] SKIPPED (not a news site): {url[:70]}")
            continue

        try:
            print(f"     📥  [FIRECRAWL] [{i}/{total}] Scraping news: {url[:70]} …")
            page = app.scrape(url)

            if not page or not page.markdown:
                print(f"     ⚠️  [FIRECRAWL] [{i}/{total}] No content extracted")
                continue

            markdown = page.markdown[:5000]

            # ── Filter 2: Reject historical / non-current content ──
            if not _looks_like_current_news(markdown):
                print(f"     🚫  [FIRECRAWL] [{i}/{total}] SKIPPED (historical/archive content)")
                continue

            print(f"     ✅  [FIRECRAWL] [{i}/{total}] Got {len(markdown)} chars: {item.title[:60]}")

            contents.append(
                f"NEWS SOURCE: {item.title}\n"
                f"URL: {item.url}\n"
                f"---\n"
                f"{markdown}\n"
            )
        except Exception as e:
            print(f"     ❌  [FIRECRAWL] [{i}/{total}] Failed: {e}")
            continue

    if not contents:
        print("     ⚠️  [FIRECRAWL] No current news articles found after filtering")
        return (
            "No current flood news articles found. "
            "All results were either from non-news sites or contained historical data."
        )

    print(f"     ✅  [FIRECRAWL] Done — {len(contents)} current news articles scraped")
    return "\n\n===\n\n".join(contents)


def get_flood_scraper_tools():
    """Return the list of tools for the flood web scraper agent."""
    return [firecrawl_flood_search]
