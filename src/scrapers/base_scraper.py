import requests
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from src.parsers.common_schema import CommonListing, validate_listing
from src.utils.logger import get_logger


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = get_logger(f"scraper_{platform_name.lower()}")
        self.session = self._create_session()
        self.listings_processed = 0
        self.errors = []

    def _create_session(self) -> requests.Session:
        """Create requests session with default headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        return session

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
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                self.logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Failed to fetch {url} after {retries} attempts")
                    self.errors.append(f"Fetch error: {url}")
                    return None

    def fetch_json(self, url: str, timeout: int = 30, retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch and parse JSON from URL."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
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
