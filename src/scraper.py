"""Scrape the book catalog from books.toscrape.com (a sandbox site built for practice)."""
import argparse
import logging
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
USER_AGENT = "learning-scraper/1.0 (portfolio project)"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def allowed_by_robots(url: str) -> bool:
    """Check robots.txt before scraping."""
    parser = RobotFileParser(urljoin(BASE_URL, "robots.txt"))
    try:
        parser.read()
    except Exception as exc:  # robots.txt unreachable: be conservative only if it errors hard
        log.warning("Could not read robots.txt (%s); continuing cautiously", exc)
        return True
    return parser.can_fetch(USER_AGENT, url)


def fetch(session: requests.Session, url: str, retries: int = 3) -> str:
    """GET a page with simple retry and exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"  # the site omits the charset, which breaks the £ sign
            return resp.text
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def parse_page(html: str, page_url: str):
    """Extract books from one listing page; return (books, next_page_url or None)."""
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for article in soup.select("article.product_pod"):
        link = article.h3.a
        rating_word = article.select_one("p.star-rating")["class"][1]
        books.append(
            {
                "title": link["title"],
                "price_gbp": float(article.select_one("p.price_color").text.strip().lstrip("£Â")),
                "rating": RATINGS.get(rating_word),
                "in_stock": "in stock" in article.select_one("p.availability").text.lower(),
                "url": urljoin(page_url, link["href"]),
            }
        )
    next_link = soup.select_one("li.next a")
    return books, urljoin(page_url, next_link["href"]) if next_link else None


def scrape(delay: float = 1.0, max_pages: int | None = None) -> pd.DataFrame:
    if not allowed_by_robots(START_URL):
        raise SystemExit("Scraping disallowed by robots.txt")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    all_books, url, page = [], START_URL, 0
    while url and (max_pages is None or page < max_pages):
        page += 1
        log.info("Scraping page %d: %s", page, url)
        books, url = parse_page(fetch(session, url), url)
        all_books.extend(books)
        time.sleep(delay)  # be polite: rate limit between requests

    return pd.DataFrame(all_books).drop_duplicates(subset="url")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--max-pages", type=int, default=None, help="limit pages (for testing)")
    ap.add_argument("--output", default="data/books.csv")
    args = ap.parse_args()

    df = scrape(args.delay, args.max_pages)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    log.info("Saved %d books to %s", len(df), args.output)


if __name__ == "__main__":
    main()
