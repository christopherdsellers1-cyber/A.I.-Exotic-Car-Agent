"""
Scraper for Rennlist - Porsche enthusiast forum marketplace.
https://www.rennlist.com/forums/market/
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base_scraper import BaseScraper
from src.parsers.common_schema import (
    CommonListing, parse_price, parse_mileage, parse_year
)


class RennlistScraper(BaseScraper):
    """Scraper for Rennlist forum marketplace listings."""

    BASE_URL = "https://www.rennlist.com"
    MARKETPLACE_URL = "https://www.rennlist.com/forums/market/vehicles"

    def __init__(self):
        super().__init__("RENNLIST")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def scrape(self) -> List[CommonListing]:
        """Scrape Rennlist marketplace for Porsche listings."""
        all_listings = []
        self.logger.info("Starting Rennlist scrape")

        listings = self._scrape_marketplace()
        all_listings.extend(listings)

        valid_listings = self.validate_and_add(all_listings)
        self.log_run_summary(len(all_listings), len(valid_listings))

        return valid_listings

    def _scrape_marketplace(self) -> List[CommonListing]:
        """Scrape the Rennlist marketplace listings."""
        listings = []
        page = 1

        while True:
            url = f"{self.MARKETPLACE_URL}?page={page}" if page > 1 else self.MARKETPLACE_URL

            self.logger.debug(f"Scraping Rennlist page {page}: {url}")

            html = self.fetch(url)
            if not html:
                break

            page_listings = self._parse_marketplace_page(html)
            if not page_listings:
                break

            listings.extend(page_listings)
            page += 1

            # Limit pages to prevent excessive scraping
            if page > 5:
                break

        return listings

    def _parse_marketplace_page(self, html: str) -> List[CommonListing]:
        """Parse marketplace listing page."""
        listings = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Rennlist uses forum structure - look for post threads
            # Threads are usually in table rows or divs
            thread_rows = (
                soup.find_all('tr', class_=re.compile('thread|post', re.I)) or
                soup.find_all('div', class_=re.compile('thread|listing|post', re.I)) or
                soup.find_all('li', class_=re.compile('thread|thread-item', re.I))
            )

            for thread_row in thread_rows:
                # Get thread title/link
                title_elem = thread_row.find(['a', 'span'], class_=re.compile('title|subject', re.I))
                if not title_elem:
                    title_elem = thread_row.find('a')

                if not title_elem:
                    continue

                url = title_elem.get('href', '') or title_elem.find('a', href=True)
                if isinstance(url, str) and not url.startswith('http'):
                    url = f"{self.BASE_URL}{url}"
                elif not isinstance(url, str):
                    url_elem = title_elem.find('a', href=True) if title_elem else None
                    if url_elem:
                        url = url_elem.get('href', '')
                        if not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"

                if not url or not isinstance(url, str):
                    continue

                title = title_elem.get_text(strip=True)
                if not title or 'porsche' not in title.lower():
                    continue

                listing = self._parse_thread_listing(title, url, thread_row)
                if listing:
                    listings.append(listing)

        except Exception as e:
            self.logger.debug(f"Failed to parse marketplace page: {e}")

        return listings

    def _parse_thread_listing(self, title: str, url: str, thread_row) -> Optional[CommonListing]:
        """Parse a thread listing from marketplace."""
        try:
            # Platform ID from URL
            platform_id = self._extract_id_from_url(url)

            # Extract year from title
            year = self._extract_year_from_text(title)

            # Extract model and generation from title
            model, generation = self._extract_model_info(title)

            if not model or not year:
                return None

            # Extract price from title/row
            price = self._extract_price_from_text(title + ' ' + thread_row.get_text())

            # Extract mileage if present in title
            mileage_match = re.search(r'(\d+)\s*(?:miles?|km)', title, re.I)
            mileage = None
            if mileage_match:
                mileage = parse_mileage(mileage_match.group(1))

            # Transmission from title
            transmission = None
            title_lower = title.lower()
            if 'manual' in title_lower:
                transmission = 'Manual'
            elif 'pdk' in title_lower or 'automatic' in title_lower:
                transmission = 'PDK'

            # Extract location from thread (often in title as city/state)
            location = self._extract_location_from_title(title)

            # Get thread content/description for features
            thread_content = thread_row.get_text(strip=True)
            features = self._extract_features(thread_content)

            # Check condition if mentioned
            condition = self._extract_condition(thread_content)

            listing = CommonListing(
                platform='RENNLIST',
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
                seller_location=location,
                features=features,
            )

            return listing

        except Exception as e:
            self.logger.debug(f"Failed to parse thread listing: {e}")
            return None

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extract thread ID from URL."""
        # Rennlist URLs often have thread number
        match = re.search(r'/(\d+)(?:-|/|$)', url)
        if match:
            return match.group(1)
        match = re.search(r'thread[_=](\d+)', url, re.I)
        if match:
            return match.group(1)
        return str(hash(url))

    @staticmethod
    def _extract_year_from_text(text: str) -> Optional[int]:
        """Extract year from text."""
        # Look for 4-digit year at start (common format: "2015 Porsche 911 GT3")
        match = re.search(r'\b(19|20)\d{2}\b', text)
        if match:
            year = parse_year(match.group(0))
            return year
        return None

    @staticmethod
    def _extract_model_info(title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract model and generation from title."""
        title_upper = title.upper()

        model = None
        generation = None

        if 'GT3 RS' in title_upper or 'GT3RS' in title_upper:
            model = 'GT3 RS'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2018', '2019', '18', '19']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT3' in title_upper:
            model = 'GT3'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2' if any(y in title for y in ['2017', '2018', '2019', '17', '18', '19']) else '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT2' in title_upper:
            model = 'GT2 RS'
            if '991' in title:
                generation = '991.2'

        elif 'TOURING' in title_upper and 'GT3' in title_upper:
            model = 'GT3 Touring'
            if '992' in title:
                generation = '992.1'
            elif '991' in title:
                generation = '991.2'

        elif '911' in title_upper:
            model = '911'

        return model, generation

    @staticmethod
    def _extract_price_from_text(text: str) -> Optional[float]:
        """Extract price from text."""
        # Look for price patterns: $XXX,XXX or asking $XXX,XXX
        price_match = re.search(r'\$[\d,]+', text)
        if price_match:
            return parse_price(price_match.group(0))

        # Look for "asking" prefix
        asking_match = re.search(r'asking\s+\$[\d,]+', text, re.I)
        if asking_match:
            price = re.search(r'\$[\d,]+', asking_match.group(0))
            if price:
                return parse_price(price.group(0))

        return None

    @staticmethod
    def _extract_location_from_title(title: str) -> Optional[str]:
        """Extract location (state abbreviation or city) from title."""
        # Look for state abbreviations (CA, TX, etc.)
        states = [
            'CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI',
            'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MD', 'CO', 'OR',
            'MN', 'MO', 'WI', 'SC', 'AL', 'LA', 'KY', 'OK', 'NM', 'NV',
            'AR', 'MS', 'KS', 'UT', 'NE', 'ID', 'HI', 'NH', 'ME', 'MT',
            'DE', 'SD', 'ND', 'AK', 'RI', 'VT', 'WV', 'WY',
        ]

        # Look for "location:" prefix
        location_match = re.search(r'location:?\s*([A-Z]{2})', title, re.I)
        if location_match:
            return location_match.group(1)

        # Check for state codes in title
        for state in states:
            if f' {state} ' in title or f'({state})' in title or title.endswith(state):
                return state

        return None

    @staticmethod
    def _extract_features(text: str) -> List[str]:
        """Extract features from listing text."""
        features = []
        text_lower = text.lower()

        feature_keywords = {
            'bucket seats': ['bucket', 'race bucket', 'sport bucket'],
            'carbon-ceramic brakes': ['pccb', 'pcb', 'carbon ceramic', 'carbon brake'],
            'weissach package': ['weissach'],
            'chrono package': ['chrono', 'sport chrono'],
            'manual transmission': ['manual', '6-speed'],
            'front-axle lift': ['axle lift', 'lift'],
            'porsche exclusive': ['exclusive', 'manufaktur'],
        }

        for feature_name, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature_name)

        return features

    @staticmethod
    def _extract_condition(text: str) -> Optional[str]:
        """Extract condition from text."""
        text_lower = text.lower()

        if 'excellent' in text_lower or 'mint' in text_lower:
            return 'Excellent'
        elif 'very good' in text_lower:
            return 'Very Good'
        elif 'good' in text_lower:
            return 'Good'
        elif 'fair' in text_lower:
            return 'Fair'
        elif 'restoration' in text_lower or 'project' in text_lower:
            return 'Restoration'

        return None
