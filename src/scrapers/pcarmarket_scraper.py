"""
Scraper for PCARMARKET - Porsche specialist auction marketplace.
https://www.pcarmarket.com
"""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base_scraper import BaseScraper
from src.parsers.common_schema import (
    CommonListing, parse_price, parse_mileage, parse_year,
    normalize_model_name, normalize_transmission, normalize_title_status
)


class PcarmarketScraper(BaseScraper):
    """Scraper for PCARMARKET.COM listings."""

    BASE_URL = "https://www.pcarmarket.com"

    SEARCH_PATHS = {
        'all_models': '/auction',
        'gt3': '/auction?model=911%20GT3',
        'gt3_rs': '/auction?model=911%20GT3%20RS',
        'gt2_rs': '/auction?model=911%20GT2%20RS',
    }

    def __init__(self):
        super().__init__("PCARMARKET")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml',
        })

    def scrape(self) -> List[CommonListing]:
        """Scrape PCARMARKET for Porsche listings."""
        all_listings = []
        self.logger.info("Starting PCARMARKET scrape")

        # Try JSON API first, fall back to HTML parsing
        listings = self._scrape_api() or self._scrape_html()

        if listings:
            all_listings.extend(listings)
            self.logger.info(f"Found {len(listings)} listings")

        valid_listings = self.validate_and_add(all_listings)
        self.log_run_summary(len(all_listings), len(valid_listings))

        return valid_listings

    def _scrape_api(self) -> Optional[List[CommonListing]]:
        """Try to scrape via JSON API if available."""
        listings = []

        try:
            # PCARMARKET may have a JSON endpoint
            api_url = f"{self.BASE_URL}/api/auctions"
            data = self.fetch_json(api_url)

            if not data:
                return None

            # Parse API response
            items = data.get('items', []) or data.get('auctions', []) or data.get('results', [])

            for item in items:
                listing = self._parse_api_item(item)
                if listing:
                    listings.append(listing)

            return listings if listings else None

        except Exception as e:
            self.logger.debug(f"API scrape failed, will try HTML: {e}")
            return None

    def _scrape_html(self) -> List[CommonListing]:
        """Scrape PCARMARKET via HTML parsing."""
        listings = []

        try:
            url = f"{self.BASE_URL}/auction"
            html = self.fetch(url)

            if not html:
                return listings

            soup = BeautifulSoup(html, 'lxml')

            # Find auction items (PCARMARKET specific structure)
            auction_items = soup.find_all(['div', 'article'], class_=re.compile('auction|item|lot', re.I))

            for item in auction_items:
                listing = self._parse_html_item(item)
                if listing:
                    listings.append(listing)

        except Exception as e:
            self.logger.error(f"HTML scrape failed: {e}")

        return listings

    def _parse_api_item(self, item: dict) -> Optional[CommonListing]:
        """Parse API response item."""
        try:
            # Extract URL
            url = item.get('url') or item.get('link') or ""
            if url and not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"

            title = item.get('title') or item.get('description') or ""
            if not title or not url:
                return None

            # Extract data
            price = parse_price(str(item.get('price', '')))
            mileage = parse_mileage(str(item.get('mileage', '')))
            year = parse_year(str(item.get('year', '')))

            # Model info
            model, generation = self._extract_model_info(title)

            # Platform ID
            platform_id = item.get('id') or item.get('lot_id') or self._extract_id_from_url(url)

            # Status (active, sold, pending)
            status = item.get('status', 'active').lower()
            if status not in ['active', 'pending']:
                return None

            # Features from description
            features = self._extract_features(title + ' ' + item.get('description', ''))

            # Transmission
            transmission = None
            text_lower = (title + ' ' + item.get('description', '')).lower()
            if 'manual' in text_lower:
                transmission = 'Manual'
            elif 'pdk' in text_lower or 'automatic' in text_lower:
                transmission = 'PDK'

            # Estimate vs hammer price
            estimate_min = item.get('estimate_min')
            estimate_max = item.get('estimate_max')
            hammer_price = item.get('hammer_price')

            # Use price, falling back to estimate high
            if not price and estimate_max:
                price = float(estimate_max)

            listing = CommonListing(
                platform='PCARMARKET',
                platform_id=str(platform_id),
                url=url,
                title=title,
                model=model,
                generation=generation,
                year=year,
                price=price,
                mileage=mileage,
                transmission=transmission,
                features=features,
            )

            return listing

        except Exception as e:
            self.logger.debug(f"Failed to parse API item: {e}")
            return None

    def _parse_html_item(self, container) -> Optional[CommonListing]:
        """Parse HTML listing item."""
        try:
            # Extract URL
            link_elem = container.find('a', href=True)
            if not link_elem:
                return None

            url = link_elem.get('href', '')
            if not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"

            # Extract title
            title_elem = container.find(['h2', 'h3', 'h4', 'a'])
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                return None

            # Platform ID
            platform_id = self._extract_id_from_url(url)

            # Price
            price_elem = container.find(string=re.compile(r'\$.*\d+'))
            price = parse_price(str(price_elem)) if price_elem else None

            # Mileage
            mileage_elem = container.find(string=re.compile(r'\d+\s*miles?|km'))
            mileage = parse_mileage(str(mileage_elem)) if mileage_elem else None

            # Year
            year = self._extract_year_from_text(title)

            # Model info
            model, generation = self._extract_model_info(title)

            # Transmission
            transmission = None
            text_lower = container.get_text(strip=True).lower()
            if 'manual' in text_lower:
                transmission = 'Manual'
            elif 'pdk' in text_lower or 'automatic' in text_lower:
                transmission = 'PDK'

            # Features
            features = self._extract_features(container.get_text(strip=True))

            listing = CommonListing(
                platform='PCARMARKET',
                platform_id=platform_id,
                url=url,
                title=title,
                model=model,
                generation=generation,
                year=year,
                price=price,
                mileage=mileage,
                transmission=transmission,
                features=features,
            )

            return listing

        except Exception as e:
            self.logger.debug(f"Failed to parse HTML item: {e}")
            return None

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extract ID from URL."""
        # Look for lot number or ID in URL
        match = re.search(r'/(\d+)/?$', url)
        if match:
            return match.group(1)
        match = re.search(r'lot[_-]?(\d+)', url, re.I)
        if match:
            return match.group(1)
        return str(hash(url))

    @staticmethod
    def _extract_year_from_text(text: str) -> Optional[int]:
        """Extract year from text."""
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        if years:
            year = parse_year(years[0])
            return year
        return None

    @staticmethod
    def _extract_model_info(title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract model and generation from title."""
        title_upper = title.upper()

        model = None
        generation = None

        if 'GT3 RS' in title_upper:
            model = 'GT3 RS'
            if '992' in title or '9921' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2018', '2019']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT3' in title_upper and 'GT2' not in title_upper:
            model = 'GT3'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2017', '2018', '2019']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT2 RS' in title_upper:
            model = 'GT2 RS'
            if '991' in title:
                generation = '991.2'

        elif 'TOURING' in title_upper and 'GT3' in title_upper:
            model = 'GT3 Touring'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2'

        return model, generation

    @staticmethod
    def _extract_features(text: str) -> List[str]:
        """Extract features from text."""
        features = []
        text_lower = text.lower()

        feature_keywords = {
            'bucket seats': ['bucket seat', 'bucket', 'race bucket', 'sport bucket'],
            'carbon-ceramic brakes': ['pccb', 'pcb', 'carbon ceramic', 'carbon brake'],
            'weissach package': ['weissach package', 'weissach'],
            'chrono package': ['sport chrono', 'chrono package'],
            'manual transmission': ['manual', 'manual transmission'],
            'front-axle lift': ['front-axle lift', 'axle lift'],
            'porsche exclusive': ['porsche exclusive', 'exclusive'],
        }

        for feature_name, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature_name)

        return features
