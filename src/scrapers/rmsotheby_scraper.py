"""
Scraper for RM Sotheby's - Prestigious auction house.
https://www.rmsothebys.com
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from src.scrapers.base_scraper import BaseScraper
from src.parsers.common_schema import (
    CommonListing, parse_price, parse_mileage, parse_year
)


class RmsothebyScraper(BaseScraper):
    """Scraper for RM Sotheby's auction listings."""

    BASE_URL = "https://www.rmsothebys.com"

    def __init__(self):
        super().__init__("RM_SOTHEBY'S")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def scrape(self) -> List[CommonListing]:
        """Scrape RM Sotheby's for upcoming and current Porsche auctions."""
        all_listings = []
        self.logger.info("Starting RM Sotheby's scrape")

        # RM Sotheby's has multiple auction events throughout the year
        # Try to find Porsche lots from recent and upcoming auctions
        listings = self._scrape_upcoming_auctions()
        all_listings.extend(listings)

        valid_listings = self.validate_and_add(all_listings)
        self.log_run_summary(len(all_listings), len(valid_listings))

        return valid_listings

    def _scrape_upcoming_auctions(self) -> List[CommonListing]:
        """Scrape upcoming auction events and their Porsche listings."""
        listings = []

        try:
            # Get main auctions page
            auctions_url = f"{self.BASE_URL}/en/auctions"
            html = self.fetch(auctions_url)

            if not html:
                return listings

            soup = BeautifulSoup(html, 'lxml')

            # Find auction event cards
            auction_events = soup.find_all(['a', 'div'], class_=re.compile('auction|event|sale', re.I))

            for event in auction_events[:10]:  # Limit to recent 10 events
                # Extract event URL
                event_link = event.find('a', href=True)
                if not event_link:
                    continue

                event_url = event_link.get('href', '')
                if not event_url.startswith('http'):
                    event_url = f"{self.BASE_URL}{event_url}"

                # Scrape individual auction event for Porsche lots
                event_listings = self._scrape_auction_event(event_url)
                listings.extend(event_listings)

        except Exception as e:
            self.logger.error(f"Failed to scrape upcoming auctions: {e}")

        return listings

    def _scrape_auction_event(self, event_url: str) -> List[CommonListing]:
        """Scrape a specific auction event for Porsche lots."""
        listings = []

        try:
            html = self.fetch(event_url)
            if not html:
                return listings

            soup = BeautifulSoup(html, 'lxml')

            # Find lot items in auction
            # RM Sotheby's uses various HTML structures, try multiple selectors
            lot_containers = (
                soup.find_all('div', class_=re.compile('lot|item', re.I)) or
                soup.find_all('article') or
                soup.find_all('div', class_=re.compile('vehicle', re.I))
            )

            for lot in lot_containers:
                # Check if it's a Porsche
                lot_text = lot.get_text(strip=True).lower()
                if 'porsche' not in lot_text:
                    continue

                listing = self._parse_lot_item(lot, event_url)
                if listing:
                    listings.append(listing)

        except Exception as e:
            self.logger.debug(f"Failed to scrape event {event_url}: {e}")

        return listings

    def _parse_lot_item(self, lot_elem, event_url: str) -> Optional[CommonListing]:
        """Parse a single lot item."""
        try:
            # Extract lot link
            lot_link = lot_elem.find('a', href=True)
            if not lot_link:
                return None

            url = lot_link.get('href', '')
            if not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"

            # Extract lot number/ID
            platform_id = self._extract_lot_id(url)

            # Title
            title_elem = lot_elem.find(['h2', 'h3', 'h4', 'span'])
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                title = lot_link.get_text(strip=True)

            if not title:
                return None

            # Estimate and/or hammer price
            lot_text = lot_elem.get_text(strip=True)
            price = self._extract_price_from_lot(lot_text)

            # Mileage
            mileage_match = re.search(r'(\d+)\s*miles?', lot_text, re.I)
            mileage = parse_mileage(mileage_match.group(1)) if mileage_match else None

            # Year
            year = self._extract_year_from_text(title)

            # Model and generation
            model, generation = self._extract_model_info(title)

            # Transmission
            transmission = None
            if 'manual' in lot_text.lower():
                transmission = 'Manual'
            elif 'pdk' in lot_text.lower() or 'automatic' in lot_text.lower():
                transmission = 'PDK'

            # Features from lot description
            features = self._extract_features(lot_text)

            # Condition report (if available)
            condition = self._extract_condition(lot_text)

            # Auction status
            status_text = lot_text.lower()
            if 'sold' in status_text or 'hammer' in status_text:
                status = 'sold'
            elif 'upcoming' in status_text or 'lot' in status_text:
                status = 'active'
            else:
                status = 'active'

            # Only include active/pending auctions
            if status != 'active':
                return None

            listing = CommonListing(
                platform='RM_SOTHEBY\'S',
                platform_id=platform_id,
                url=url,
                title=title,
                model=model,
                generation=generation,
                year=year,
                price=price,
                mileage=mileage,
                transmission=transmission,
                condition=condition,
                features=features,
            )

            return listing

        except Exception as e:
            self.logger.debug(f"Failed to parse lot: {e}")
            return None

    @staticmethod
    def _extract_lot_id(url: str) -> str:
        """Extract lot ID from URL."""
        # Try pattern: /auctions/.../lots/r0123-...
        match = re.search(r'/lots/([^/]+)', url)
        if match:
            return match.group(1)
        # Try pattern: lot=123
        match = re.search(r'lot[_=](\d+)', url, re.I)
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
    def _extract_price_from_lot(text: str) -> Optional[float]:
        """Extract price from lot text (estimate or hammer price)."""
        # Look for hammer price first
        hammer_match = re.search(r'hammer price:\s*\$[\d,]+', text, re.I)
        if hammer_match:
            price_str = re.search(r'\$[\d,]+', hammer_match.group(0))
            if price_str:
                return parse_price(price_str.group(0))

        # Look for estimate high
        estimate_match = re.search(r'estimate:\s*\$[\d,]+\s*-\s*\$[\d,]+', text, re.I)
        if estimate_match:
            prices = re.findall(r'\$[\d,]+', estimate_match.group(0))
            if prices:
                return parse_price(prices[-1])  # Use high estimate

        # Generic price match
        price_match = re.search(r'\$[\d,]+', text)
        if price_match:
            return parse_price(price_match.group(0))

        return None

    @staticmethod
    def _extract_model_info(title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract model and generation."""
        title_upper = title.upper()

        model = None
        generation = None

        if 'GT3 RS' in title_upper:
            model = 'GT3 RS'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2018', '2019']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT3' in title_upper:
            model = 'GT3'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2017', '2018', '2019']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT2' in title_upper:
            model = 'GT2 RS'
            if '991' in title:
                generation = '991.2'

        elif 'TOURING' in title_upper:
            model = 'GT3 Touring'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2'

        elif 'CARRERA' in title_upper:
            model = 'Carrera'

        return model, generation

    @staticmethod
    def _extract_features(text: str) -> List[str]:
        """Extract features from lot description."""
        features = []
        text_lower = text.lower()

        feature_keywords = {
            'bucket seats': ['bucket seat', 'bucket', 'race bucket'],
            'carbon-ceramic brakes': ['pccb', 'carbon ceramic', 'carbon brake'],
            'weissach package': ['weissach', 'weissach package'],
            'chrono package': ['sport chrono', 'chrono'],
            'manual transmission': ['manual', '6-speed manual'],
            'front-axle lift': ['front-axle lift', 'axle lift'],
            'porsche exclusive': ['porsche exclusive', 'exclusive'],
        }

        for feature_name, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature_name)

        return features

    @staticmethod
    def _extract_condition(text: str) -> Optional[str]:
        """Extract condition assessment."""
        text_lower = text.lower()

        if 'excellent' in text_lower:
            return 'Excellent'
        elif 'very good' in text_lower:
            return 'Very Good'
        elif 'good' in text_lower:
            return 'Good'
        elif 'fair' in text_lower:
            return 'Fair'
        elif 'restoration' in text_lower:
            return 'Restoration'

        return None
