"""
Scraper for Elferspot - European Porsche specialist marketplace.
https://www.elferspot.com
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base_scraper import BaseScraper
from src.parsers.common_schema import (
    CommonListing, parse_price, parse_mileage, parse_year
)


class ElfersportScraper(BaseScraper):
    """Scraper for Elferspot European Porsche marketplace."""

    BASE_URL = "https://www.elferspot.com"

    # Elferspot is in German, but we can find Porsches via search
    SEARCH_PATHS = {
        'porsche_gt3': '/en/find/porsche-911-gt3-for-sale',
        'porsche_gt3_rs': '/en/find/porsche-911-gt3-rs-for-sale',
        'porsche_gt2_rs': '/en/find/porsche-911-gt2-rs-for-sale',
        'porsche_touring': '/en/find/porsche-911-touring-for-sale',
    }

    def __init__(self):
        super().__init__("ELFERSPOT")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
        })

    def scrape(self) -> List[CommonListing]:
        """Scrape Elferspot for Porsche listings."""
        all_listings = []
        self.logger.info("Starting Elferspot scrape")

        for model_key, search_path in self.SEARCH_PATHS.items():
            try:
                listings = self._scrape_search(search_path)
                if listings:
                    all_listings.extend(listings)
                    self.logger.info(f"Found {len(listings)} listings for {model_key}")
            except Exception as e:
                self.logger.error(f"Error scraping {model_key}: {e}")

        valid_listings = self.validate_and_add(all_listings)
        self.log_run_summary(len(all_listings), len(valid_listings))

        return valid_listings

    def _scrape_search(self, search_path: str) -> List[CommonListing]:
        """Scrape a search results page."""
        listings = []
        page = 1

        while True:
            # Elferspot uses pagination
            url = f"{self.BASE_URL}{search_path}?page={page}" if page > 1 else f"{self.BASE_URL}{search_path}"

            self.logger.debug(f"Scraping page {page}: {url}")

            html = self.fetch(url)
            if not html:
                break

            page_listings = self._parse_listing_page(html)
            if not page_listings:
                break

            listings.extend(page_listings)
            page += 1

            # Limit pages
            if page > 3:
                break

        return listings

    def _parse_listing_page(self, html: str) -> List[CommonListing]:
        """Parse search results page."""
        listings = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find listing containers
            listing_containers = (
                soup.find_all('div', class_=re.compile('listing|vehicle|car-item', re.I)) or
                soup.find_all('article') or
                soup.find_all('li', class_=re.compile('result', re.I))
            )

            for container in listing_containers:
                listing = self._parse_listing_item(container)
                if listing:
                    listings.append(listing)

        except Exception as e:
            self.logger.debug(f"Failed to parse listing page: {e}")

        return listings

    def _parse_listing_item(self, container) -> Optional[CommonListing]:
        """Parse a single listing item."""
        try:
            # Extract URL
            link_elem = container.find('a', href=True)
            if not link_elem:
                return None

            url = link_elem.get('href', '')
            if not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"

            # Title
            title_elem = container.find(['h2', 'h3', 'h4', 'span'])
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                title = link_elem.get_text(strip=True)

            if not title:
                return None

            # Platform ID
            platform_id = self._extract_id_from_url(url)

            # Price - Elferspot may use EUR, convert to USD estimate
            price_elem = container.find(string=re.compile(r'€|EUR|\$'))
            price_text = price_elem if price_elem else ""

            # Handle EUR to USD (rough conversion, ~1 EUR = 1.1 USD)
            price = None
            if price_text:
                price_val = parse_price(str(price_text))
                if price_val:
                    # If it's EUR, convert to USD
                    if '€' in str(price_text):
                        price = price_val * 1.1
                    else:
                        price = price_val

            # Mileage
            mileage_elem = container.find(string=re.compile(r'\d+\s*(km|miles)', re.I))
            mileage = None
            if mileage_elem:
                # Convert km to miles if needed
                mileage_str = str(mileage_elem).lower()
                if 'km' in mileage_str:
                    km = parse_mileage(str(mileage_elem))
                    if km:
                        mileage = int(km * 0.621371)  # km to miles
                else:
                    mileage = parse_mileage(str(mileage_elem))

            # Year
            year = self._extract_year_from_text(title)

            # Model and generation
            model, generation = self._extract_model_info(title)

            # Location (Elferspot shows country/region)
            location_text = container.get_text(strip=True).lower()
            location = self._extract_location(location_text)

            # Transmission
            transmission = None
            full_text = container.get_text(strip=True).lower()
            if 'manual' in full_text or 'schaltgetriebe' in full_text:
                transmission = 'Manual'
            elif 'pdk' in full_text or 'automatik' in full_text:
                transmission = 'PDK'

            # Features
            features = self._extract_features(container.get_text(strip=True))

            # Condition
            condition_text = container.get_text(strip=True)
            condition = self._extract_condition(condition_text)

            listing = CommonListing(
                platform='ELFERSPOT',
                platform_id=platform_id,
                url=url,
                title=title,
                model=model,
                generation=generation,
                year=year,
                price=price,
                price_currency='EUR' if '€' in str(price_text) else 'USD',
                mileage=mileage,
                mileage_unit='km',
                transmission=transmission,
                condition=condition,
                seller_location=location,
                features=features,
            )

            return listing

        except Exception as e:
            self.logger.debug(f"Failed to parse listing: {e}")
            return None

    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """Extract ID from URL."""
        # Elferspot uses /find/ID/ format
        match = re.search(r'/(\d+)(?:/|$)', url)
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

        elif '911' in title_upper:
            model = '911'

        return model, generation

    @staticmethod
    def _extract_features(text: str) -> List[str]:
        """Extract features."""
        features = []
        text_lower = text.lower()

        feature_keywords = {
            'bucket seats': ['bucket', 'schalensitze'],
            'carbon-ceramic brakes': ['pccb', 'carbon ceramic', 'keramik'],
            'weissach package': ['weissach'],
            'chrono package': ['chrono', 'sport chrono'],
            'manual transmission': ['manual', '6-gang'],
            'front-axle lift': ['achslift', 'lift'],
            'porsche exclusive': ['exclusive', 'manufaktur'],
        }

        for feature_name, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature_name)

        return features

    @staticmethod
    def _extract_condition(text: str) -> Optional[str]:
        """Extract condition."""
        text_lower = text.lower()

        if 'excellent' in text_lower or 'hervorragend' in text_lower:
            return 'Excellent'
        elif 'very good' in text_lower or 'sehr gut' in text_lower:
            return 'Very Good'
        elif 'good' in text_lower or 'gut' in text_lower:
            return 'Good'
        elif 'fair' in text_lower:
            return 'Fair'

        return None

    @staticmethod
    def _extract_location(text: str) -> Optional[str]:
        """Extract location (country/region)."""
        # Common European countries
        countries = {
            'germany': 'DE', 'deutschland': 'DE',
            'france': 'FR', 'frankreich': 'FR',
            'italy': 'IT', 'italien': 'IT',
            'spain': 'ES', 'spanien': 'ES',
            'uk': 'GB', 'united kingdom': 'GB', 'england': 'GB',
            'netherlands': 'NL', 'holland': 'NL',
            'belgium': 'BE', 'belgien': 'BE',
            'switzerland': 'CH', 'schweiz': 'CH',
            'austria': 'AT', 'österreich': 'AT',
        }

        for country, code in countries.items():
            if country in text.lower():
                return code

        return None
