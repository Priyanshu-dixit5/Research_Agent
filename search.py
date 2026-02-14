"""
search.py – Web Search Module
Uses multiple search backends for reliability:
  1. Wikipedia API (always works, high-quality content)
  2. DuckDuckGo Lite (simpler, less blocking)
  3. Bing search (fallback)
Returns a list of result URLs and snippets for a given research topic.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote
import time
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


def _search_wikipedia(topic: str, max_results: int = 5) -> list[dict]:
    """
    Search Wikipedia API for relevant articles.
    This is the most reliable source – always works.
    """
    results = []
    try:
        # Step 1: Search for matching article titles
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "srlimit": max_results,
            "format": "json",
            "srprop": "snippet",
        }
        resp = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()
            url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
            results.append({
                "url": url,
                "title": f"Wikipedia: {title}",
                "snippet": snippet,
            })

        print(f"[Search] Wikipedia: found {len(results)} results")

    except Exception as e:
        print(f"[Search] Wikipedia error: {e}")

    return results


def _search_duckduckgo_lite(topic: str, max_results: int = 8) -> list[dict]:
    """
    Search DuckDuckGo Lite – simpler HTML, less anti-bot measures.
    """
    results = []
    seen_urls = set()

    queries = [
        f"{topic}",
        f"{topic} research overview",
    ]

    for query in queries:
        if len(results) >= max_results:
            break
        try:
            resp = requests.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # DuckDuckGo Lite uses simple table rows for results
            for link in soup.find_all("a", class_="result-link"):
                if len(results) >= max_results:
                    break

                url = link.get("href", "")
                if not url or not url.startswith("http"):
                    continue
                if url in seen_urls:
                    continue

                # Skip non-content domains
                skip = ["youtube.com", "facebook.com", "twitter.com",
                        "instagram.com", "tiktok.com", "reddit.com",
                        "duckduckgo.com"]
                if any(d in url.lower() for d in skip):
                    continue

                title = link.get_text(strip=True)
                seen_urls.add(url)
                results.append({
                    "url": url,
                    "title": title,
                    "snippet": "",
                })

            # Also try parsing from table structure
            if not results:
                for a_tag in soup.find_all("a"):
                    href = a_tag.get("href", "")
                    text = a_tag.get_text(strip=True)
                    if (href.startswith("http") and
                        "duckduckgo.com" not in href and
                        len(text) > 10 and
                        href not in seen_urls):

                        skip_check = ["youtube.com", "facebook.com", "twitter.com",
                                      "instagram.com", "tiktok.com"]
                        if any(d in href.lower() for d in skip_check):
                            continue

                        seen_urls.add(href)
                        results.append({
                            "url": href,
                            "title": text,
                            "snippet": "",
                        })
                        if len(results) >= max_results:
                            break

            time.sleep(0.3)

        except Exception as e:
            print(f"[Search] DuckDuckGo Lite error: {e}")

    print(f"[Search] DuckDuckGo Lite: found {len(results)} results")
    return results


def _search_bing(topic: str, max_results: int = 8) -> list[dict]:
    """
    Search Bing as a fallback.
    """
    results = []
    seen_urls = set()

    try:
        url = f"https://www.bing.com/search?q={quote_plus(topic + ' research')}&count={max_results}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for li in soup.select("li.b_algo"):
            a_tag = li.select_one("h2 a")
            if not a_tag:
                continue

            href = a_tag.get("href", "")
            if not href.startswith("http") or href in seen_urls:
                continue

            title = a_tag.get_text(strip=True)
            snippet_tag = li.select_one(".b_caption p")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            seen_urls.add(href)
            results.append({
                "url": href,
                "title": title,
                "snippet": snippet,
            })

            if len(results) >= max_results:
                break

    except Exception as e:
        print(f"[Search] Bing error: {e}")

    print(f"[Search] Bing: found {len(results)} results")
    return results


def search_web(topic: str, max_results: int = 10) -> list[dict]:
    """
    Search the web using multiple backends for reliability.

    Args:
        topic: The research topic to search for.
        max_results: Maximum number of results to return.

    Returns:
        A list of dicts with keys: 'url', 'title', 'snippet'.
    """
    all_results = []
    seen_urls = set()

    # 1. Wikipedia (most reliable, best for research)
    print("[Search] Trying Wikipedia API...")
    wiki_results = _search_wikipedia(topic, max_results=4)
    for r in wiki_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            all_results.append(r)

    # 2. DuckDuckGo Lite
    print("[Search] Trying DuckDuckGo Lite...")
    ddg_results = _search_duckduckgo_lite(topic, max_results=6)
    for r in ddg_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            all_results.append(r)

    # 3. Bing (fallback)
    if len(all_results) < 4:
        print("[Search] Trying Bing search...")
        bing_results = _search_bing(topic, max_results=6)
        for r in bing_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    # Trim to max
    all_results = all_results[:max_results]
    print(f"[Search] Total: {len(all_results)} results for '{topic}'")
    return all_results


if __name__ == "__main__":
    results = search_web("Quantum Computing")
    for r in results:
        print(f"  {r['title'][:60]}  →  {r['url'][:80]}")
