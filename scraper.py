"""
scraper.py – Web Content Extraction Module
Fetches HTML pages and extracts clean, relevant text content
using BeautifulSoup. Also can fetch Wikipedia content via API.
Merges content from multiple sources into a consolidated research corpus.
"""

import requests
from bs4 import BeautifulSoup, Comment
import re


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Tags to completely remove from the DOM
STRIP_TAGS = [
    "script", "style", "nav", "footer", "header", "aside",
    "form", "iframe", "noscript", "svg", "button", "input",
    "select", "textarea", "menu", "dialog",
]

# CSS classes / IDs that typically contain non-content
NOISE_PATTERNS = re.compile(
    r"(sidebar|comment|advert|banner|popup|modal|cookie|consent|"
    r"share|social|related|recommend|newsletter|subscribe|promo|"
    r"widget|footer|nav|menu|breadcrumb)",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    """Normalize whitespace and clean up extracted text."""
    text = re.sub(r"\s+", " ", text)
    lines = text.split(". ")
    lines = [l.strip() for l in lines if len(l.strip()) > 30]
    return ". ".join(lines)


def _fetch_wikipedia_content(url: str) -> str:
    """
    Fetch Wikipedia article content via the MediaWiki API.
    Much more reliable than scraping the HTML page.
    """
    try:
        # Extract the article title from URL
        title = url.split("/wiki/")[-1] if "/wiki/" in url else ""
        if not title:
            return ""

        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title.replace("_", " "),
            "prop": "extracts",
            "exintro": False,      # Get full content, not just intro
            "explaintext": True,   # Plain text, not HTML
            "format": "json",
            "exsectionformat": "plain",
        }

        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                return ""
            content = page.get("extract", "")
            if content:
                # Limit length
                if len(content) > 8000:
                    content = content[:8000] + "..."
                print(f"[Scraper] Wikipedia API: got {len(content)} chars for '{title}'")
                return content

    except Exception as e:
        print(f"[Scraper] Wikipedia API error: {e}")

    return ""


def _is_valid_content_url(url: str) -> bool:
    """Check if a URL looks like a real content page worth scraping."""
    skip_patterns = [
        "duckduckgo.com/y.js",
        "duckduckgo.com/duckduckgo-help",
        "/ad_", "ad_domain=", "ad_provider=", "ad_type=",
        ".js?", "/aclick?",
        "doubleclick.net", "googlesyndication.com",
    ]
    return not any(p in url for p in skip_patterns)


def extract_content(url: str, timeout: int = 10) -> str:
    """
    Fetch a URL and extract the main textual content.

    Args:
        url: The page URL to scrape.
        timeout: Request timeout in seconds.

    Returns:
        Cleaned text content from the page, or empty string on failure.
    """
    # Skip ad/tracking/junk URLs
    if not _is_valid_content_url(url):
        print(f"[Scraper] Skipping non-content URL: {url[:80]}...")
        return ""

    # Use Wikipedia API for Wikipedia URLs (much more reliable)
    if "wikipedia.org/wiki/" in url:
        content = _fetch_wikipedia_content(url)
        if content:
            return content

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unwanted tags
        for tag_name in STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Remove noisy elements
        for el in soup.find_all(True):
            try:
                classes = " ".join(el.get("class", []) or [])
                el_id = el.get("id", "") or ""
                if NOISE_PATTERNS.search(classes) or NOISE_PATTERNS.search(el_id):
                    el.decompose()
            except (AttributeError, TypeError):
                continue

        # Find the main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"role": "main"})
            or soup.find("div", class_=re.compile(r"(content|article|post|entry)", re.I))
            or soup.body
        )

        if not main_content:
            return ""

        # Extract text from paragraphs, headings, and list items
        text_parts = []
        for tag in main_content.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = tag.get_text(strip=True)
            if len(text) > 20:
                text_parts.append(text)

        raw_text = " ".join(text_parts)
        return _clean_text(raw_text)

    except requests.RequestException as e:
        print(f"[Scraper] Failed to fetch {url}: {e}")
        return ""
    except Exception as e:
        print(f"[Scraper] Error processing {url}: {e}")
        return ""


def scrape_and_merge(search_results: list[dict], max_pages: int = 6) -> str:
    """
    Scrape content from multiple search results and merge into
    a single research corpus.

    Args:
        search_results: List of dicts with 'url', 'title', 'snippet'.
        max_pages: Maximum number of pages to scrape.

    Returns:
        Merged, deduplicated content string.
    """
    all_content = []
    pages_scraped = 0

    for result in search_results:
        if pages_scraped >= max_pages:
            break

        url = result.get("url", "")
        print(f"[Scraper] Fetching: {url[:80]}...")

        content = extract_content(url)
        if content and len(content) > 200:
            title = result.get("title", "Source")
            all_content.append(f"[Source: {title}]\n{content}")
            pages_scraped += 1

    if not all_content:
        # Fallback: use snippets from search results
        print("[Scraper] No page content extracted, using search snippets.")
        snippets = [r.get("snippet", "") for r in search_results if r.get("snippet")]
        if snippets:
            return " ".join(snippets)
        # Last resort: return topic description
        return "Limited information available from web sources."

    merged = "\n\n---\n\n".join(all_content)

    # Truncate to avoid context-window issues
    max_chars = 25000
    if len(merged) > max_chars:
        merged = merged[:max_chars] + "\n\n[Content truncated for processing...]"

    print(f"[Scraper] Extracted {len(merged)} chars from {pages_scraped} pages")
    return merged


if __name__ == "__main__":
    from search import search_web
    results = search_web("Quantum Computing", max_results=5)
    corpus = scrape_and_merge(results, max_pages=3)
    print(f"\n--- Corpus Preview (first 500 chars) ---\n{corpus[:500]}")
