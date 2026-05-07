"""
Data Processing and Transformation Module.
Handles normalization, validation, and transformation of listing data.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
from src.utils.logger import get_logger


@dataclass
class ProcessingResult:
    """Result of data processing operation."""
    success: bool
    data: Optional[Dict] = None
    errors: List[str] = None
    warnings: List[str] = None
    transformations: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.transformations is None:
            self.transformations = {}


class DataProcessor:
    """
    Processes and normalizes listing data.
    Handles validation, deduplication, and transformation.
    """

    def __init__(self):
        self.logger = get_logger("data_processor")
        self.price_cache: Dict[str, float] = {}  # For tracking price histories
        self.seen_listings: Dict[str, str] = {}  # For deduplication

    def process_listing(self, listing: Dict) -> ProcessingResult:
        """
        Process a single listing through all validation and normalization steps.

        Args:
            listing: Raw listing dictionary from scraper

        Returns:
            ProcessingResult with cleaned data and any issues
        """
        errors = []
        warnings = []
        transformations = {}

        # Make a copy to avoid modifying original
        cleaned = listing.copy()

        # Validate required fields
        required_fields = ['title', 'price', 'url']
        for field in required_fields:
            if not cleaned.get(field):
                errors.append(f"Missing required field: {field}")
                return ProcessingResult(success=False, errors=errors)

        # Normalize prices
        price_result = self.normalize_price(cleaned.get('price'))
        if price_result['valid']:
            cleaned['price'] = price_result['normalized']
            if price_result['transformed']:
                transformations['price'] = price_result
        else:
            errors.append(f"Invalid price: {cleaned.get('price')}")

        # Normalize mileage
        if cleaned.get('mileage') is not None:
            mileage_result = self.normalize_mileage(cleaned.get('mileage'))
            if mileage_result['valid']:
                cleaned['mileage'] = mileage_result['normalized']
                if mileage_result['transformed']:
                    transformations['mileage'] = mileage_result
            else:
                warnings.append(f"Invalid mileage: {cleaned.get('mileage')}")
                cleaned['mileage'] = None

        # Normalize year
        if cleaned.get('year'):
            year_result = self.normalize_year(cleaned.get('year'))
            if year_result['valid']:
                cleaned['year'] = year_result['normalized']
                if year_result['transformed']:
                    transformations['year'] = year_result
            else:
                warnings.append(f"Invalid year: {cleaned.get('year')}")

        # Normalize location
        if cleaned.get('location'):
            cleaned['location'] = self.normalize_location(cleaned['location'])

        # Normalize and deduplicate title/model
        if cleaned.get('title'):
            cleaned['title'] = self.normalize_title(cleaned['title'])

        # Validate URL format
        if not self.is_valid_url(cleaned.get('url', '')):
            warnings.append(f"Suspicious URL format: {cleaned.get('url')}")

        # Check for duplicate
        dedup_key = self.generate_dedup_key(cleaned)
        if dedup_key in self.seen_listings:
            errors.append(f"Duplicate listing detected (seen at {self.seen_listings[dedup_key]})")
            return ProcessingResult(success=False, errors=errors)

        self.seen_listings[dedup_key] = cleaned.get('url', 'unknown')

        success = len(errors) == 0
        return ProcessingResult(
            success=success,
            data=cleaned if success else None,
            errors=errors,
            warnings=warnings,
            transformations=transformations,
        )

    def normalize_price(self, price: Any) -> Dict[str, Any]:
        """
        Normalize price to float USD.

        Returns:
            Dict with 'valid', 'normalized', 'transformed', 'original'
        """
        if isinstance(price, (int, float)):
            return {
                'valid': True,
                'normalized': float(price),
                'transformed': False,
                'original': price,
            }

        if isinstance(price, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$€£,]', '', price).strip()

            # Handle 'asking' prices
            cleaned = re.sub(r'asking\s+', '', cleaned, flags=re.IGNORECASE)

            try:
                value = float(cleaned)
                transformed = price != str(value)  # Changed from original?
                return {
                    'valid': True,
                    'normalized': value,
                    'transformed': transformed,
                    'original': price,
                }
            except ValueError:
                return {
                    'valid': False,
                    'normalized': None,
                    'transformed': False,
                    'original': price,
                }

        return {
            'valid': False,
            'normalized': None,
            'transformed': False,
            'original': price,
        }

    def normalize_mileage(self, mileage: Any) -> Dict[str, Any]:
        """
        Normalize mileage to integer miles.

        Returns:
            Dict with 'valid', 'normalized', 'transformed', 'original'
        """
        if isinstance(mileage, int):
            return {
                'valid': True,
                'normalized': mileage,
                'transformed': False,
                'original': mileage,
            }

        if isinstance(mileage, str):
            # Remove commas and 'km' or 'miles' units
            cleaned = mileage.lower().replace('km', '').replace('miles', '').replace('mi', '')
            cleaned = re.sub(r'[,\s]', '', cleaned).strip()

            try:
                value = int(float(cleaned))
                # If original had 'km', convert to miles
                transformed = 'km' in mileage.lower()
                if transformed:
                    value = int(value * 0.621371)  # km to miles

                return {
                    'valid': True,
                    'normalized': value,
                    'transformed': transformed,
                    'original': mileage,
                    'unit_conversion': 'km->miles' if transformed else None,
                }
            except ValueError:
                return {
                    'valid': False,
                    'normalized': None,
                    'transformed': False,
                    'original': mileage,
                }

        return {
            'valid': False,
            'normalized': None,
            'transformed': False,
            'original': mileage,
        }

    def normalize_year(self, year: Any) -> Dict[str, Any]:
        """
        Normalize year to integer (1995-2030).

        Returns:
            Dict with 'valid', 'normalized', 'transformed', 'original'
        """
        if isinstance(year, int) and 1990 <= year <= 2030:
            return {
                'valid': True,
                'normalized': year,
                'transformed': False,
                'original': year,
            }

        if isinstance(year, str):
            # Extract 4-digit year
            match = re.search(r'(19|20)\d{2}', year)
            if match:
                value = int(match.group(0))
                if 1990 <= value <= 2030:
                    return {
                        'valid': True,
                        'normalized': value,
                        'transformed': year != str(value),
                        'original': year,
                    }

        return {
            'valid': False,
            'normalized': None,
            'transformed': False,
            'original': year,
        }

    def normalize_location(self, location: str) -> str:
        """Normalize location string."""
        if not location:
            return ""

        # Remove extra whitespace and normalize case
        location = ' '.join(location.split()).title()

        # Standardize state codes if present
        state_map = {
            'CA': 'California',
            'NY': 'New York',
            'TX': 'Texas',
            'FL': 'Florida',
            'IL': 'Illinois',
            'PA': 'Pennsylvania',
            'OH': 'Ohio',
            'GA': 'Georgia',
            'NC': 'North Carolina',
            'AZ': 'Arizona',
        }

        for code, name in state_map.items():
            location = re.sub(rf'\b{code}\b', name, location, flags=re.IGNORECASE)

        return location

    def normalize_title(self, title: str) -> str:
        """Normalize listing title."""
        if not title:
            return ""

        # Remove extra whitespace
        title = ' '.join(title.split())

        # Remove common redundant patterns
        title = re.sub(r'\s*\(.*?\)\s*', ' ', title)  # Remove parentheticals
        title = re.sub(r'for sale|for\s+sale|fsbo', '', title, flags=re.IGNORECASE)
        title = re.sub(r'low\s*miles|low\s*mileage', 'low miles', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()  # Clean whitespace

        return title

    def normalize_features(self, features: List[str]) -> List[str]:
        """
        Normalize feature list by deduplication and standardization.

        Returns:
            Deduplicated, lowercased features
        """
        if not features:
            return []

        # Standardize feature names
        standard_features = {
            'bucket seats': ['bucket seats', 'sport seats', 'sport bucket seats'],
            'carbon brakes': ['carbon brakes', 'carbon ceramic', 'pccb', 'ceramic brakes'],
            'weissach': ['weissach package', 'weissach', 'weissach pkg'],
            'magnesium wheels': ['magnesium wheels', 'mag wheels', 'forged wheels'],
            'manual transmission': ['manual transmission', 'manual', 'stick shift', 'mt'],
            'pts paint': ['pts paint', 'paint to sample', 'custom paint'],
            'g6 engine': ['g6 engine', 'g6', 'gen 6 engine'],
            'warranty': ['warranty', 'porsche warranty', 'factory warranty'],
            'service records': ['service records', 'documented service', 'full service history'],
            'clean title': ['clean title', 'no accidents', 'clean history'],
        }

        normalized = set()
        for feature in features:
            feature_lower = feature.lower()

            # Find matching standard feature
            matched = False
            for standard, variants in standard_features.items():
                if any(variant in feature_lower for variant in variants):
                    normalized.add(standard)
                    matched = True
                    break

            # If no match found, add as-is (lowercased)
            if not matched:
                normalized.add(feature_lower)

        return sorted(list(normalized))

    def is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        if not url or not isinstance(url, str):
            return False

        url_pattern = re.compile(
            r'^https?://'  # http or https
            r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*'  # subdomains
            r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'  # domain
            r'(?:\.[a-zA-Z]{2,})?'  # TLD
            r'(?:/.*)?$'  # path
        )
        return bool(url_pattern.match(url))

    def generate_dedup_key(self, listing: Dict) -> str:
        """
        Generate deduplication key from listing data.

        Listings are considered duplicates if they have same
        title, price, location, and URL domain (within tolerance).
        """
        title = listing.get('title', '').lower()
        price = int(listing.get('price', 0))
        location = listing.get('location', '').lower()
        url = listing.get('url', '')

        # Extract domain from URL
        domain_match = re.search(r'://([^/]+)', url)
        domain = domain_match.group(1) if domain_match else ''

        # Create key with tolerance for small price variations (±2%)
        price_band = (price // 2000) * 2000  # Group by $2000 bands

        return f"{title}|{price_band}|{location}|{domain}"

    def batch_process_listings(
        self,
        listings: List[Dict],
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Any]]:
        """
        Process multiple listings and return clean + problematic + stats.

        Returns:
            (clean_listings, problematic_listings, stats)
        """
        clean = []
        problematic = []
        stats = {
            'total': len(listings),
            'valid': 0,
            'invalid': 0,
            'duplicates': 0,
            'errors': [],
            'warnings': [],
        }

        for listing in listings:
            result = self.process_listing(listing)

            if result.success:
                clean.append(result.data)
                stats['valid'] += 1
            else:
                problematic.append({
                    'listing': listing,
                    'errors': result.errors,
                    'warnings': result.warnings,
                })
                stats['invalid'] += 1
                if 'Duplicate' in str(result.errors):
                    stats['duplicates'] += 1

            stats['errors'].extend(result.errors)
            stats['warnings'].extend(result.warnings)

        stats['success_rate'] = (stats['valid'] / stats['total'] * 100) if stats['total'] > 0 else 0

        self.logger.info(
            f"Batch processing: {stats['valid']}/{stats['total']} valid "
            f"({stats['success_rate']:.1f}%)"
        )

        return clean, problematic, stats


# Global instance
_processor = None


def get_data_processor() -> DataProcessor:
    """Get global data processor instance."""
    global _processor
    if _processor is None:
        _processor = DataProcessor()
    return _processor
