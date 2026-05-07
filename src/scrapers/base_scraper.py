import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from src.parsers.common_schema import CommonListing, validate_listing
from src.utils.logger import get_logger

# Prefer curl-cffi for Chrome TLS impersonation (bypasses Cloudflare fingerprinting).
# Falls back to standard requests if not installed.
try:
    from curl_cffi import requests
    from curl_cffi.requests import Session as _BaseSession
    _CURL_AVAILABLE = True
    _IMPERSONATE = "chrome124"
except ImportError:
    import requests
    _BaseSession = requests.Session
    _CURL_AVAILABLE = False
    _IMPERSONATE = None

# Realistic browser user-agents (rotate to reduce fingerprinting)
_USER_AGENTS = [
    (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0'
    ),
    (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) '
        'Version/17.4.1 Safari/605.1.15'
    ),
]


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = get_logger(f"scraper_{platform_name.lower()}")
        self.session = self._create_session()
        self.listings_processed = 0
        self.errors = []

    def _create_session(self):
        """Create session with Chrome TLS impersonation when available."""
        if _CURL_AVAILABLE:
            # curl-cffi handles TLS fingerprint + all browser headers automatically
            return requests.Session(impersonate=_IMPERSONATE)
        else:
            # Fallback: standard requests with realistic browser headers
            session = requests.Session()
            session.headers.update({
                'User-Agent': random.choice(_USER_AGENTS),
                'Accept': (
                    'text/html,application/xhtml+xml,application/xml;'
                    'q=0.9,image/avif,image/webp,image/apng,*/*;'
                    'q=0.8,application/signed-exchange;v=b3;q=0.7'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            })
            return session

    def _human_delay(self, min_s: float = 1.0, max_s: float = 3.5):
        """Random delay between requests to avoid rate limiting."""
        time.sleep(random.uniform(min_s, max_s))

    @abstractmethod
    def scrape(self) -> List[CommonListing]:
        """
        Main scrape method.
        Should return list of CommonListing objects.
        Subclasses must implement.
        """
        pass

    def fetch(self, url: str, timeout: int = 30, retries: int = 3) -> Optional[str]:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            retries: Number of retry attempts

        Returns:
            Response content or None if failed
        """
        for attempt in range(retries):
            try:
                if attempt > 0:
                    if not _CURL_AVAILABLE:
                        self.session.headers.update({'User-Agent': random.choice(_USER_AGENTS)})
                    self._human_delay(2.0, 5.0)

                kwargs = {'timeout': timeout}
                if _CURL_AVAILABLE:
                    kwargs['impersonate'] = _IMPERSONATE
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                self._human_delay()
                return response.text
            except Exception as e:
                self.logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Failed to fetch {url} after {retries} attempts")
                    self.errors.append(f"Fetch error: {url}")
                    return None

    def fetch_json(self, url: str, timeout: int = 30, retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch and parse JSON from URL."""
        for attempt in range(retries):
            try:
                if attempt > 0:
                    if not _CURL_AVAILABLE:
                        self.session.headers.update({'User-Agent': random.choice(_USER_AGENTS)})
                    self._human_delay(2.0, 5.0)

                kwargs = {'timeout': timeout}
                if _CURL_AVAILABLE:
                    kwargs['impersonate'] = _IMPERSONATE
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                self._human_delay()
                return response.json()
            except Exception as e:
                self.logger.warning(f"JSON fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Failed to fetch JSON from {url}")
                    self.errors.append(f"JSON fetch error: {url}")
                    return None

    def validate_and_add(self, listings: List[CommonListing]) -> List[CommonListing]:
        """
        Validate listings and return only valid ones.
        Logs errors for invalid listings.
        """
        valid_listings = []

        for listing in listings:
            is_valid, errors = validate_listing(listing)
            if is_valid:
                valid_listings.append(listing)
            else:
                self.logger.warning(f"Invalid listing from {listing.url}: {', '.join(errors)}")
                self.errors.append(f"Validation error: {listing.title}")

        return valid_listings

    def log_run_summary(self, total_found: int, total_processed: int):
        """Log scrape run summary."""
        self.logger.info(
            f"{self.platform_name} scrape completed: "
            f"Found {total_found}, Processed {total_processed}, "
            f"Errors: {len(self.errors)}"
        )

    def __del__(self):
        """Close session when scraper is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()


class ScraperPool:
    """Manage multiple scrapers."""

    def __init__(self, scrapers: List[BaseScraper]):
        self.scrapers = scrapers
        self.logger = get_logger("scraper_pool")

    def scrape_all(self) -> List[CommonListing]:
        """Run all scrapers and combine results."""
        all_listings = []

        for scraper in self.scrapers:
            try:
                self.logger.info(f"Starting scrape of {scraper.platform_name}")
                listings = scraper.scrape()
                all_listings.extend(listings)
                scraper.log_run_summary(len(listings), scraper.listings_processed)
            except Exception as e:
                self.logger.error(f"Scraper {scraper.platform_name} failed: {e}")

        self.logger.info(f"Total listings collected: {len(all_listings)}")
        return all_listings

    def scrape_by_platform(self, platform: str) -> List[CommonListing]:
        """Scrape a specific platform."""
        for scraper in self.scrapers:
            if scraper.platform_name.lower() == platform.lower():
                try:
                    return scraper.scrape()
                except Exception as e:
                    self.logger.error(f"Scraper {platform} failed: {e}")
                    return []
        return []
