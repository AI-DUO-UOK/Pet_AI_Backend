"""
5-crawl_recursive_internal_links.py
----------------------------------
Recursively crawls a site starting from a root URL, using Crawl4AI's arun_many and a memory-adaptive dispatcher.
Extracts clean article-quality text suitable for RAG pipelines — strips navigation, icons, junk links,
and boilerplate. Only pages passing a content quality filter are saved.

Usage: Set the start URL and max_depth in main(), then run as a script.
Output: One .txt file per page saved to OUTPUT_DIR, plus a JSONL manifest file.
"""
import asyncio
import json
import re
import os
from pathlib import Path
from urllib.parse import urldefrag, urlparse
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
    MemoryAdaptiveDispatcher
)

from pathlib import Path

# Get project root (go 2 levels up from crawler.py → chatbot/ → project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Now define output inside chatbot/
OUTPUT_DIR = BASE_DIR / "rag_output"

MANIFEST_FILE = OUTPUT_DIR / "manifest.jsonl"
PREVIEW_CHARS = 300

# Ensure directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)                       # Chars to preview in console per page

# ── Content quality filter thresholds ────────────────────────────
MIN_CLEAN_CHARS = 300        # Skip pages with fewer clean chars than this
MIN_PARAGRAPH_COUNT = 2      # Skip pages with fewer real paragraphs than this

# ── URL path segments that indicate junk/utility pages ───────────
SKIP_URL_PATTERNS = [
    "/login", "/logout", "/signup", "/register", "/cart", "/checkout",
    "/search", "/tag/", "/category/", "/author/", "/page/",
    "/privacy", "/terms", "/disclaimer", "/cookie", "/sitemap",
    "/about", "/contact", "/permissions", "/partnerships",
    "/quizzes", "/quiz", "/resourcespages", "/resource",
    "javascript:", "mailto:", "#",
]


# ─────────────────────────────────────────────────────────────────
# URL helpers
# ─────────────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """Remove URL fragment (the #section part)."""
    return urldefrag(url)[0]


def should_skip_url(url: str) -> bool:
    """Return True if this URL looks like a utility/junk page we don't want."""
    url_lower = url.lower()
    return any(pat in url_lower for pat in SKIP_URL_PATTERNS)


def url_to_filename(url: str) -> str:
    """Convert a URL to a safe filename (no special chars)."""
    parsed = urlparse(url)
    path = (parsed.netloc + parsed.path).strip("/").replace("/", "__")
    path = re.sub(r"[^\w\-.]", "_", path)
    return path[:180] + ".txt"   # cap length for filesystem safety


# ─────────────────────────────────────────────────────────────────
# Markdown → clean article text
# ─────────────────────────────────────────────────────────────────

# Lines that are almost certainly navigation / boilerplate
_JUNK_LINE_PATTERNS = [
    re.compile(r"^\s*\[.*?\]\(.*?\)\s*$"),                   # bare markdown link lines
    re.compile(r"!\[.*?\]\(.*?\)"),                           # image tags
    re.compile(r"data:image/", re.IGNORECASE),                # base64 images
    re.compile(r"^\s*[*\-]\s*\[.*?\]\(https?://.*?\)\s*$"),  # bullet nav links
    re.compile(r"skip to (main|content)", re.IGNORECASE),
    re.compile(r"^\s*(expand all|collapse all)\s*$", re.IGNORECASE),
    re.compile(r"^\s*cookie(s| preferences)", re.IGNORECASE),
    re.compile(r"^\s*(accept|reject) cookies", re.IGNORECASE),
    re.compile(r"^\s*copyright©?\s*\d{4}", re.IGNORECASE),
    re.compile(r"honeypot", re.IGNORECASE),
    re.compile(r"^\s*(follow us|view our)", re.IGNORECASE),
    re.compile(r"^\s*english\s*$", re.IGNORECASE),            # lone language selectors
    re.compile(r"_next/static|_next/image|sitecorecloud"),    # Next.js / CDN internals
    re.compile(r"^\s*#{1,6}\s*$"),                            # empty headings
    re.compile(r"^={3,}$|^-{3,}$"),                          # pure horizontal rules
]

# Heading pattern
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")


def _is_junk_line(line: str) -> bool:
    return any(pat.search(line) for pat in _JUNK_LINE_PATTERNS)


def _is_real_paragraph(line: str) -> bool:
    """
    A real paragraph: not a heading, not a list item, not a bare link,
    at least 60 characters, and contains enough words to look like prose.
    """
    stripped = line.strip()
    if len(stripped) < 60:
        return False
    if _HEADING_RE.match(stripped):
        return False
    if stripped.startswith(("- ", "* ", "+ ", "1.", "2.")):
        return False
    if len(stripped.split()) < 6:
        return False
    return True


def clean_markdown_to_article(markdown: str) -> str:
    """
    Convert raw Crawl4AI markdown to clean article text for RAG ingestion.
    - Strips navigation, images, boilerplate, and junk link lines
    - Collapses repeated blank lines
    - Preserves headings and real prose paragraphs
    """
    lines = markdown.splitlines()
    clean_lines = []
    prev_blank = False

    for line in lines:
        if _is_junk_line(line):
            continue

        stripped = line.strip()

        # Collapse multiple blank lines into one
        if not stripped:
            if not prev_blank and clean_lines:
                clean_lines.append("")
            prev_blank = True
            continue

        prev_blank = False
        clean_lines.append(stripped)

    return "\n".join(clean_lines).strip()


def is_quality_content(text: str) -> tuple[bool, int, int]:
    """
    Returns (passes, char_count, paragraph_count).
    A page passes if it has enough chars AND enough real paragraphs.
    """
    char_count = len(text)
    paragraph_count = sum(1 for line in text.splitlines() if _is_real_paragraph(line))
    passes = char_count >= MIN_CLEAN_CHARS and paragraph_count >= MIN_PARAGRAPH_COUNT
    return passes, char_count, paragraph_count


# ─────────────────────────────────────────────────────────────────
# Main crawler
# ─────────────────────────────────────────────────────────────────

async def crawl_recursive_batch(start_urls, max_depth=3, max_concurrent=10):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_fh = open(MANIFEST_FILE, "w", encoding="utf-8")

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=False
    )
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent
    )

    visited = set()
    saved_count = 0
    skipped_quality = 0
    skipped_url = 0

    current_urls = {normalize_url(u) for u in start_urls}

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for depth in range(max_depth):
            print(f"\n{'='*60}")
            print(f"  Crawling Depth {depth + 1} / {max_depth}")
            print(f"{'='*60}")

            urls_to_crawl = [
                u for u in (normalize_url(u) for u in current_urls)
                if u not in visited and not should_skip_url(u)
            ]
            url_filtered_count = sum(
                1 for u in (normalize_url(u) for u in current_urls)
                if u not in visited and should_skip_url(u)
            )
            skipped_url += url_filtered_count

            if not urls_to_crawl:
                print("No new URLs to crawl. Stopping.")
                break

            print(f"  Queued: {len(urls_to_crawl)} | URL-filtered out: {url_filtered_count}")

            results = await crawler.arun_many(
                urls=urls_to_crawl,
                config=run_config,
                dispatcher=dispatcher
            )

            next_level_urls = set()

            for result in results:
                norm_url = normalize_url(result.url)
                visited.add(norm_url)

                print(f"\n{'─'*60}")

                if not result.success:
                    print(f"[ERROR] {result.url}")
                    print(f"        {result.error_message}")
                    continue

                if not result.markdown:
                    print(f"[SKIP-EMPTY] {result.url}")
                    continue

                # ── Clean and quality-filter ──────────────────────
                clean_text = clean_markdown_to_article(result.markdown)
                passes, char_count, para_count = is_quality_content(clean_text)

                if not passes:
                    skipped_quality += 1
                    print(f"[SKIP-QUALITY] {result.url}")
                    print(f"               {char_count} chars, {para_count} paragraphs "
                          f"(min: {MIN_CLEAN_CHARS} chars / {MIN_PARAGRAPH_COUNT} paras)")
                else:
                    # ── Save to disk ──────────────────────────────
                    filename = url_to_filename(norm_url)
                    filepath = OUTPUT_DIR / filename
                    filepath.write_text(clean_text, encoding="utf-8")

                    # Append to manifest
                    record = {
                        "url": norm_url,
                        "file": filename,
                        "chars": char_count,
                        "paragraphs": para_count,
                        "depth": depth + 1,
                    }
                    manifest_fh.write(json.dumps(record) + "\n")
                    manifest_fh.flush()

                    saved_count += 1
                    print(f"[SAVED] {result.url}")
                    print(f"        {char_count} chars | {para_count} paragraphs | → {filename}")
                    print(f"\n  ── Preview ──")
                    print(clean_text[:PREVIEW_CHARS])
                    if char_count > PREVIEW_CHARS:
                        print(f"  ... [{char_count - PREVIEW_CHARS} more chars]")

                # ── Collect internal links regardless of quality ──
                for link in result.links.get("internal", []):
                    next_url = normalize_url(link["href"])
                    if next_url not in visited and not should_skip_url(next_url):
                        next_level_urls.add(next_url)

            print(f"\n── Depth {depth + 1} done: {len(results)} crawled | "
                  f"{saved_count} saved so far | "
                  f"{len(next_level_urls)} queued next ──")

            current_urls = next_level_urls

    manifest_fh.close()

    print(f"\n{'='*60}")
    print(f"  Crawl complete.")
    print(f"  Pages visited  : {len(visited)}")
    print(f"  Pages saved    : {saved_count}  →  {OUTPUT_DIR}/")
    print(f"  Skipped (URL)  : {skipped_url}")
    print(f"  Skipped (qual) : {skipped_quality}")
    print(f"  Manifest       : {MANIFEST_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(crawl_recursive_batch(
        start_urls=["https://www.msdvetmanual.com/cat-owners"],
        max_depth=2,
        max_concurrent=10
    ))