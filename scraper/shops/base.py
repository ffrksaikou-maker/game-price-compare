"""Base class for all shop scrapers."""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    """A single scraped product with name and buyback price."""
    name: str
    price: int  # buyback price in yen (0 = not available)


class BaseScraper(ABC):
    """Base class for shop scrapers."""

    shop_id: str = ""
    shop_name: str = ""
    use_playwright: bool = False

    # Common HTTP headers
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    @abstractmethod
    def scrape(self) -> list[ScrapedItem]:
        """Scrape the shop and return a list of items with prices."""

    def _get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        """Fetch a URL and return a BeautifulSoup object."""
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=30, **kwargs)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                logger.warning(
                    "%s: attempt %d failed for %s: %s",
                    self.shop_name, attempt + 1, url, e,
                )
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise

    @staticmethod
    def parse_price(text: str) -> int:
        """Extract an integer price from text like '¥14,300' or '14300円'."""
        if not text:
            return 0
        # Remove all non-digit characters
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else 0
