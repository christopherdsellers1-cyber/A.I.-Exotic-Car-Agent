from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib


@dataclass
class CommonListing:
    """
    Unified listing schema across all platforms.
    This is what scrapers should produce.
    """
    platform: str
    platform_id: str
    url: str
    title: str
    model: Optional[str] = None
    generation: Optional[str] = None
    year: Optional[int] = None
    price: Optional[float] = None
    price_currency: str = 'USD'
    mileage: Optional[int] = None
    mileage_unit: str = 'miles'
    condition: Optional[str] = None
    transmission: Optional[str] = None
    title_status: Optional[str] = None
    owner_count: Optional[int] = None
    features: List[str] = field(default_factory=list)
    has_service_records: bool = False
    has_accidents: bool = False
    seller_name: Optional[str] = None
    seller_location: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    raw_html: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_updated_at'] = self.last_updated_at.isoformat()
        return data

    def generate_hash(self) -> str:
        """Generate hash for deduplication."""
        key = f"{self.platform}_{self.platform_id}_{self.url}_{self.title}_{self.price}"
        return hashlib.md5(key.encode()).hexdigest()

    def normalize_features(self) -> List[str]:
        """Normalize feature list to lowercase."""
        return [f.lower().strip() for f in self.features if f]

    def has_feature(self, feature: str) -> bool:
        """Check if listing has a specific feature."""
        feature_lower = feature.lower()
        return any(feature_lower in f.lower() for f in self.features)

    def __repr__(self):
        return (
            f"<CommonListing("
            f"{self.platform}, "
            f"{self.model} {self.year}, "
            f"${self.price}, "
            f"{self.mileage} miles"
            f")>"
        )


def validate_listing(listing: CommonListing) -> tuple[bool, List[str]]:
    """
    Validate a listing has minimum required fields.
    Returns (is_valid, list_of_errors)
    """
    errors = []

    if not listing.platform:
        errors.append("Missing platform")
    if not listing.platform_id:
        errors.append("Missing platform_id")
    if not listing.url:
        errors.append("Missing URL")
    if not listing.title:
        errors.append("Missing title")
    if listing.year is None or listing.year < 1950 or listing.year > 2030:
        errors.append(f"Invalid year: {listing.year}")
    if listing.price is None or listing.price <= 0:
        errors.append(f"Invalid price: {listing.price}")
    if listing.mileage is not None and (listing.mileage < 0 or listing.mileage > 500000):
        errors.append(f"Suspicious mileage: {listing.mileage}")

    return len(errors) == 0, errors


def parse_price(price_str: str) -> Optional[float]:
    """Parse price string to float."""
    if not price_str:
        return None
    try:
        clean = price_str.replace('$', '').replace(',', '').replace('€', '').strip()
        return float(clean)
    except ValueError:
        return None


def parse_mileage(mileage_str: str) -> Optional[int]:
    """Parse mileage string to integer."""
    if not mileage_str:
        return None
    try:
        clean = mileage_str.lower().replace('miles', '').replace('km', '').replace(',', '').strip()
        return int(float(clean))
    except ValueError:
        return None


def parse_year(year_str: str) -> Optional[int]:
    """Parse year string to integer."""
    if not year_str:
        return None
    try:
        clean = year_str.strip()
        year = int(clean)
        if 1950 <= year <= 2030:
            return year
    except ValueError:
        pass
    return None


def normalize_model_name(model: str) -> str:
    """Normalize model name for matching."""
    if not model:
        return ""
    # Standard model variations
    model = model.upper()
    model = model.replace('911 ', '')
    model = model.replace('PORSCHE ', '')
    return model.strip()


def normalize_transmission(transmission: str) -> Optional[str]:
    """Normalize transmission type."""
    if not transmission:
        return None
    trans_lower = transmission.lower()
    if 'manual' in trans_lower or '6-speed' in trans_lower:
        return 'Manual'
    elif 'pdk' in trans_lower or 'automatic' in trans_lower or 'pdks' in trans_lower:
        return 'PDK'
    return transmission


def normalize_title_status(title_str: str) -> Optional[str]:
    """Normalize title status."""
    if not title_str:
        return None
    title_lower = title_str.lower()
    if 'clean' in title_lower:
        return 'Clean'
    elif 'salvage' in title_lower:
        return 'Salvage'
    elif 'branded' in title_lower:
        return 'Branded'
    elif 'flood' in title_lower:
        return 'Flood'
    return title_str
