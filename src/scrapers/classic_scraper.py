"""
Scraper for CLASSIC.COM - Major classic/exotic car marketplace.
https://www.classic.com
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base_scraper import BaseScraper
from src.parsers.common_schema import (
    CommonListing, parse_price, parse_mileage, parse_year,
    normalize_model_name, normalize_transmission, normalize_title_status
)


class ClassicScraper(BaseScraper):
    """Scraper for CLASSIC.COM listings."""

    BASE_URL = "https://www.classic.com"

    # Search URLs for different Porsche models
    SEARCH_PATHS = {
        'gt3': '/porsche/911/991/gt3',
        'gt3_touring': '/porsche/911/991/touring',
        'gt3_rs': '/porsche/911/gt3-rs',
        'gt2_rs': '/porsche/911/gt2-rs',
        '911_touring': '/porsche/911/touring',
    }

    def __init__(self):
        super().__init__("CLASSIC.COM")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
        })

    def scrape(self) -> List[CommonListing]:
        """
        Scrape CLASSIC.COM for Porsche listings.
        Returns list of CommonListing objects.
        """
        all_listings = []
        self.logger.info(f"Starting CLASSIC.COM scrape")

        for model_key, search_path in self.SEARCH_PATHS.items():
            try:
                listings = self._scrape_model(model_key, search_path)
                if listings:
                    all_listings.extend(listings)
                    self.logger.info(f"Found {len(listings)} listings for {model_key}")
            except Exception as e:
                self.logger.error(f"Error scraping {model_key}: {e}")
                self.errors.append(f"Model {model_key}: {str(e)}")

        # Validate and return
        valid_listings = self.validate_and_add(all_listings)
        self.log_run_summary(len(all_listings), len(valid_listings))

        return valid_listings

    def _scrape_model(self, model_key: str, search_path: str) -> List[CommonListing]:
        """Scrape a specific model search page."""
        listings = []
        page = 1

        while True:
            url = f"{self.BASE_URL}{search_path}?page={page}"
            self.logger.debug(f"Scraping page {page}: {url}")

            html = self.fetch(url)
            if not html:
                break

            page_listings = self._parse_listing_page(html)
            if not page_listings:
                # No more listings
                break

            listings.extend(page_listings)
            page += 1

            # Limit pages to avoid excessive scraping
            if page > 5:
                self.logger.info(f"Reached page limit for {model_key}")
                break

        return listings

    def _parse_listing_page(self, html: str) -> List[CommonListing]:
        """Parse HTML page and extract listing cards."""
        listings = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find listing containers (CLASSIC.COM structure may vary)
            # Common selectors to try
            listing_containers = (
                soup.find_all('div', class_=re.compile('listing|card|vehicle', re.I)) or
                soup.find_all('article') or
                soup.find_all('li', class_=re.compile('result', re.I))
            )

            for container in listing_containers:
                try:
                    listing = self._parse_listing_card(container)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    self.logger.debug(f"Failed to parse card: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to parse listing page: {e}")

        return listings

    def _parse_listing_card(self, container) -> Optional[CommonListing]:
        """Parse a single listing card."""

        # Extract URL
        link_elem = container.find('a', href=True)
        if not link_elem:
            return None

        url = link_elem.get('href', '')
        if not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"

        # Extract title
        title_elem = container.find(['h2', 'h3', 'a'])
        title = title_elem.get_text(strip=True) if title_elem else ""
        if not title:
            return None

        # Platform ID from URL
        platform_id = self._extract_id_from_url(url)

        # Price
        price_elem = container.find(string=re.compile(r'\$.*\d+'))
        price_text = price_elem if price_elem else ""
        price = parse_price(str(price_text))

        # Mileage
        mileage_elem = container.find(string=re.compile(r'\d+\s*miles?'))
        mileage_text = mileage_elem if mileage_elem else ""
        mileage = parse_mileage(str(mileage_text))

        # Year - try to extract from title
        year = self._extract_year_from_text(title)

        # Model name from title
        model, generation = self._extract_model_info(title)

        # Condition (if mentioned)
        condition_text = container.get_text(strip=True).lower()
        condition = "Unknown"
        if 'mint' in condition_text:
            condition = "Mint"
        elif 'excellent' in condition_text:
            condition = "Excellent"
        elif 'very good' in condition_text:
            condition = "Very Good"
        elif 'good' in condition_text:
            condition = "Good"
        elif 'fair' in condition_text:
            condition = "Fair"

        # Extract features from text
        features = self._extract_features(container.get_text(strip=True))

        # Transmission
        transmission = None
        full_text_lower = container.get_text(strip=True).lower()
        if 'manual' in full_text_lower:
            transmission = 'Manual'
        elif 'pdk' in full_text_lower or 'automatic' in full_text_lower:
            transmission = 'PDK'

        # Location/Seller info
        location_text = container.get_text(strip=True)
        location = self._extract_location(location_text)

        # Create listing
        listing = CommonListing(
            platform='CLASSIC.COM',
            platform_id=platform_id,
            url=url,
            title=title,
            model=model,
            generation=generation,
            year=year,
            price=price,
            mileage=mileage,
            condition=condition,
            transmission=transmission,
            seller_location=location,
            features=features,
        )

        return listing

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extract listing ID from URL."""
        # Try to extract ID from URL pattern
        parts = url.split('/')
        for part in reversed(parts):
            if part.isdigit():
                return part
        # Fallback to URL hash
        return str(hash(url))

    @staticmethod
    def _extract_year_from_text(text: str) -> Optional[int]:
        """Extract year from text."""
        # Look for 4-digit numbers between 1950 and 2030
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        if years:
            year_str = years[0]  # Get first match
            year = parse_year(year_str)
            if year:
                return year
        return None

    @staticmethod
    def _extract_model_info(title: str) -> tuple[Optional[str], Optional[str]]:
        """Extract model and generation from title."""
        title_upper = title.upper()

        # Model name
        model = None
        generation = None

        if 'GT3 RS' in title_upper:
            model = 'GT3 RS'
            # Try to determine generation
            if '992' in title or '9921' in title:
                generation = '992.1'
            elif '991' in title:
                if 'GT3 RS' in title and ('2018' in title or '2019' in title):
                    generation = '991.2'
                else:
                    generation = '991.1'
            elif '997' in title:
                generation = '997.1'

        elif 'GT3' in title_upper:
            model = 'GT3'
            if '992' in title or '9921' in title:
                generation = '992.1'
            elif '991' in title:
                if '2017' in title or '2018' in title or '2019' in title:
                    generation = '991.2'
                else:
                    generation = '991.1'
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

        elif '911' in title_upper:
            model = '911'

        else:
            model = title.split()[0] if title else None

        return model, generation

    @staticmethod
    def _extract_features(text: str) -> List[str]:
        """Extract features from listing text."""
        features = []
        text_lower = text.lower()

        # Common features to look for
        feature_keywords = {
            'bucket seats': ['bucket seat', 'bucket', 'race bucket', 'sport bucket'],
            'carbon-ceramic brakes': ['pccb', 'pcb', 'carbon ceramic', 'carbon brake'],
            'weissach package': ['weissach package', 'weissach pkg', 'weissach'],
            'chrono package': ['sport chrono', 'chrono package', 'chrono'],
            'manual transmission': ['manual', 'manual transmission', '6-speed manual'],
            'front-axle lift': ['front-axle lift', 'axle lift', 'lift'],
            'porsche exclusive': ['porsche exclusive', 'exclusive manufaktur'],
        }

        for feature_name, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature_name)

        return features

    @staticmethod
    def _extract_location(text: str) -> Optional[str]:
        """Extract seller location from text."""
        # Try to find state abbreviation or city pattern
        states = [
            'CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI',
            'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MD', 'CO', 'OR',
            'MN', 'MO', 'WI', 'SC', 'AL', 'LA', 'KY', 'OK', 'NM', 'NV',
            'AR', 'MS', 'KS', 'UT', 'NE', 'ID', 'HI', 'NH', 'ME', 'MT',
            'DE', 'SD', 'ND', 'AK', 'RI', 'VT', 'WV', 'WY',
        ]

        text_parts = text.split()
        for part in text_parts:
            if part in states:
                return part

        # Return None if no location found
        return None
