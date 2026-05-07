"""
Dealer Matching and Benchmarking Module.
Identifies dealers, matches listings, and benchmarks pricing across dealers.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from src.utils.logger import get_logger


class DealerType(Enum):
    """Types of dealers in exotic car market."""
    PORSCHE_OEM = "porsche_oem"  # Official Porsche dealerships
    EXOTIC_SPECIALIST = "exotic_specialist"  # Porsche/exotic specialists
    LUXURY_DEALER = "luxury_dealer"  # General luxury dealerships
    INDEPENDENT = "independent"  # Independent dealers
    PRIVATE_SELLER = "private_seller"  # Individual sellers


@dataclass
class DealerProfile:
    """Profile of a known dealer with pricing patterns."""
    name: str
    dealer_type: DealerType
    location: str
    specialties: List[str] = field(default_factory=list)  # e.g., ['GT3', 'GT2 RS']
    average_markup_pct: float = 0.0  # Average markup above market
    reliability_score: float = 0.0  # 0-100 based on service history
    total_listings: int = 0
    avg_price_delta: float = 0.0  # Average price difference vs market
    best_model: str = ""  # Model they handle best
    known_keywords: List[str] = field(default_factory=list)  # URL/text patterns


@dataclass
class DealerMatch:
    """Result of dealer matching analysis."""
    listing_id: str
    detected_dealer: Optional[DealerProfile]
    confidence: float  # 0-100
    dealer_pricing_analysis: Dict
    recommendation: str


class DealerDatabase:
    """Known dealers and their profiles in exotic car market."""

    def __init__(self):
        self.logger = get_logger("dealer_database")
        self.dealers: Dict[str, DealerProfile] = {}
        self._initialize_known_dealers()

    def _initialize_known_dealers(self):
        """Initialize database of known dealers with profiles."""
        # Official Porsche Dealerships (OEM - typically higher pricing but best service)
        self.dealers['porsche_beverly_hills'] = DealerProfile(
            name='Porsche Beverly Hills',
            dealer_type=DealerType.PORSCHE_OEM,
            location='Los Angeles, CA',
            specialties=['992.1 GT3', '992.1 GT3 RS', '991.2 GT3'],
            average_markup_pct=8.5,
            reliability_score=95.0,
            total_listings=45,
            avg_price_delta=12500,
            best_model='992.1 GT3 RS',
            known_keywords=['porsche.com', 'beverly hills', '@porsche', 'official'],
        )

        self.dealers['porsche_monterey'] = DealerProfile(
            name='Porsche Monterey',
            dealer_type=DealerType.PORSCHE_OEM,
            location='Monterey, CA',
            specialties=['991.1 GT3', '991.2 GT3', '997.1 GT3 RS'],
            average_markup_pct=7.2,
            reliability_score=94.0,
            total_listings=38,
            avg_price_delta=9800,
            best_model='991.1 GT3',
            known_keywords=['porsche monterey', 'pebble beach', 'monterey bay'],
        )

        self.dealers['porsche_atlanta'] = DealerProfile(
            name='Porsche Atlanta',
            dealer_type=DealerType.PORSCHE_OEM,
            location='Atlanta, GA',
            specialties=['991.2 GT3', '992.1 GT3'],
            average_markup_pct=6.8,
            reliability_score=92.0,
            total_listings=32,
            avg_price_delta=8900,
            best_model='991.2 GT3',
            known_keywords=['atlanta porsche', 'georgia', 'southeast'],
        )

        # Exotic Specialists (often better pricing, strong expertise)
        self.dealers['modern_classics'] = DealerProfile(
            name='Modern Classics',
            dealer_type=DealerType.EXOTIC_SPECIALIST,
            location='Costa Mesa, CA',
            specialties=['991.1 GT3', '997.1 GT3 RS', '991.2 GT2 RS'],
            average_markup_pct=3.5,
            reliability_score=88.0,
            total_listings=92,
            avg_price_delta=4200,
            best_model='991.1 GT3',
            known_keywords=['modernclassics', 'costa mesa', 'exotic specialist'],
        )

        self.dealers['auto_fino'] = DealerProfile(
            name='Auto Fino',
            dealer_type=DealerType.EXOTIC_SPECIALIST,
            location='Torrance, CA',
            specialties=['991.2 GT3', '991.2 GT2 RS', '992.1 models'],
            average_markup_pct=4.2,
            reliability_score=87.0,
            total_listings=78,
            avg_price_delta=5800,
            best_model='991.2 GT2 RS',
            known_keywords=['autofino', 'torrance', 'porsche specialist'],
        )

        self.dealers['bison_motorsports'] = DealerProfile(
            name='Bison Motorsports',
            dealer_type=DealerType.EXOTIC_SPECIALIST,
            location='Chicago, IL',
            specialties=['991.1 GT3', '991.2 GT3', '992.1 GT3'],
            average_markup_pct=3.8,
            reliability_score=86.0,
            total_listings=64,
            avg_price_delta=4900,
            best_model='991.1 GT3',
            known_keywords=['bison motorsports', 'chicago', 'midwest exotic'],
        )

        # Luxury Dealerships (mixed bag, sometimes good deals)
        self.dealers['lamborghini_beverly_hills'] = DealerProfile(
            name='Lamborghini Beverly Hills',
            dealer_type=DealerType.LUXURY_DEALER,
            location='Los Angeles, CA',
            specialties=['992.1 GT3 RS'],
            average_markup_pct=6.5,
            reliability_score=82.0,
            total_listings=12,
            avg_price_delta=9200,
            best_model='992.1 GT3 RS',
            known_keywords=['lamborghini beverly', 'exotic supercar'],
        )

        # Independent Dealers (often best prices, variable reliability)
        # These are matched dynamically based on listing keywords
        self.dealers['independent_california'] = DealerProfile(
            name='Independent CA Dealer',
            dealer_type=DealerType.INDEPENDENT,
            location='California',
            specialties=['All GT3 variants'],
            average_markup_pct=1.5,
            reliability_score=65.0,
            total_listings=120,
            avg_price_delta=1800,
            best_model='991.1 GT3',
            known_keywords=['private dealer', 'independent', 'family owned'],
        )

        self.logger.info(f"Initialized {len(self.dealers)} known dealers")

    def get_dealer(self, dealer_id: str) -> Optional[DealerProfile]:
        """Get dealer profile by ID."""
        return self.dealers.get(dealer_id)

    def get_all_dealers(self, dealer_type: Optional[DealerType] = None) -> List[DealerProfile]:
        """Get all dealers, optionally filtered by type."""
        dealers = list(self.dealers.values())
        if dealer_type:
            dealers = [d for d in dealers if d.dealer_type == dealer_type]
        return sorted(dealers, key=lambda d: d.reliability_score, reverse=True)


class DealerMatcher:
    """
    Matches listings to dealers and analyzes pricing.
    Benchmarks listings against known dealer profiles.
    """

    def __init__(self, dealer_db: Optional[DealerDatabase] = None):
        self.logger = get_logger("dealer_matcher")
        self.db = dealer_db or DealerDatabase()
        self.price_benchmarks: Dict[str, Tuple[float, float]] = {}  # model -> (avg, std_dev)

    def match_listing_to_dealer(
        self,
        listing: Dict,
        market_value: float,
    ) -> DealerMatch:
        """
        Match a listing to a dealer and analyze pricing.

        Args:
            listing: Listing dict with url, title, price, location, etc.
            market_value: Market baseline price for this model/year

        Returns:
            DealerMatch with detected dealer and pricing analysis
        """
        listing_id = listing.get('id', 'unknown')
        url = listing.get('url', '').lower()
        title = listing.get('title', '').lower()
        location = listing.get('location', '').lower()
        price = listing.get('price', 0)

        # Try to match to known dealer
        detected_dealer = self._detect_dealer(url, title, location)

        # Analyze pricing
        pricing_analysis = self._analyze_pricing(
            price,
            market_value,
            detected_dealer,
            listing.get('model', ''),
        )

        # Generate recommendation
        recommendation = self._generate_dealer_recommendation(
            detected_dealer,
            pricing_analysis,
        )

        confidence = self._calculate_match_confidence(
            detected_dealer,
            pricing_analysis,
            url,
            title,
        )

        return DealerMatch(
            listing_id=listing_id,
            detected_dealer=detected_dealer,
            confidence=confidence,
            dealer_pricing_analysis=pricing_analysis,
            recommendation=recommendation,
        )

    def _detect_dealer(
        self,
        url: str,
        title: str,
        location: str,
    ) -> Optional[DealerProfile]:
        """Detect if listing is from known dealer."""
        search_text = f"{url} {title} {location}".lower()

        # Check keywords for each dealer
        best_match = None
        best_score = 0

        for dealer in self.db.get_all_dealers():
            score = 0
            keyword_matches = 0

            for keyword in dealer.known_keywords:
                if keyword.lower() in search_text:
                    keyword_matches += 1
                    score += 2

            # Location bonus
            if dealer.location.lower() in location:
                score += 3

            # URL domain bonus
            dealer_name_parts = dealer.name.lower().split()
            for part in dealer_name_parts:
                if len(part) > 3 and part in url:  # Avoid matching short words
                    score += 1

            if score > best_score:
                best_score = score
                best_match = dealer

        # Only return match if confidence threshold met
        if best_score >= 3:
            return best_match

        return None

    def _analyze_pricing(
        self,
        asking_price: float,
        market_value: float,
        dealer: Optional[DealerProfile],
        model: str,
    ) -> Dict:
        """Analyze pricing relative to market and dealer baseline."""
        price_diff = asking_price - market_value
        price_pct = (price_diff / market_value * 100) if market_value else 0

        # Expected markup based on dealer type
        if dealer:
            expected_markup = dealer.average_markup_pct / 100 * market_value
            markup_variance = price_diff - expected_markup
            dealer_above_baseline = markup_variance > 0
        else:
            expected_markup = 0
            markup_variance = 0
            dealer_above_baseline = False

        return {
            'market_value': market_value,
            'asking_price': asking_price,
            'price_difference': price_diff,
            'price_pct': price_pct,
            'expected_markup': expected_markup,
            'markup_variance': markup_variance,
            'dealer_above_baseline': dealer_above_baseline,
            'value_rating': self._rate_value(price_pct),
        }

    def _rate_value(self, price_pct: float) -> str:
        """Rate value based on price percentage."""
        if price_pct <= -15:
            return "EXCEPTIONAL DEAL"
        elif price_pct <= -10:
            return "EXCELLENT DEAL"
        elif price_pct <= -5:
            return "GOOD DEAL"
        elif price_pct <= 5:
            return "FAIR PRICE"
        elif price_pct <= 10:
            return "SLIGHT PREMIUM"
        elif price_pct <= 15:
            return "MODERATE PREMIUM"
        else:
            return "OVERPRICED"

    def _generate_dealer_recommendation(
        self,
        dealer: Optional[DealerProfile],
        pricing: Dict,
    ) -> str:
        """Generate recommendation based on dealer and pricing."""
        if not dealer:
            return "Unknown dealer - verify independently"

        dealer_type = dealer.dealer_type
        value = pricing.get('value_rating', 'FAIR PRICE')
        markup_var = pricing.get('markup_variance', 0)

        if dealer_type == DealerType.PORSCHE_OEM:
            if "DEAL" in value:
                return f"OEM dealer with competitive pricing - good for warranty peace of mind"
            else:
                return f"OEM dealer at typical markup - trade reliability for price"

        elif dealer_type == DealerType.EXOTIC_SPECIALIST:
            if markup_var < -5000:
                return f"Specialist dealer with excellent pricing - {dealer.name} recommended"
            elif "DEAL" in value:
                return f"Specialist with strong value - {dealer.name} has good reputation"
            else:
                return f"Specialist dealer at fair price - check {dealer.name}'s inventory"

        elif dealer_type == DealerType.INDEPENDENT:
            if "DEAL" in value:
                return f"Independent dealer with steal pricing - but verify service records"
            else:
                return f"Independent seller - verify title and maintenance history carefully"

        else:
            return f"Price is {value.lower()} - compare across other dealers"

    def _calculate_match_confidence(
        self,
        dealer: Optional[DealerProfile],
        pricing: Dict,
        url: str,
        title: str,
    ) -> float:
        """Calculate confidence score for dealer match (0-100)."""
        confidence = 0.0

        # Dealer detection confidence
        if dealer:
            confidence += 40  # Strong signal if we matched a dealer
            confidence += dealer.reliability_score * 0.3  # Bonus for reliable dealer
        else:
            confidence += 10  # Low signal for private seller

        # Price signal confidence
        price_pct = pricing.get('price_pct', 0)
        if abs(price_pct) > 20:
            confidence += 20  # Extreme prices are clearer signals
        elif abs(price_pct) > 10:
            confidence += 15
        else:
            confidence += 5  # Fair price is ambiguous

        return min(confidence, 100.0)

    def compare_dealers_for_model(
        self,
        model: str,
        listings: List[Dict],
        market_value: float,
    ) -> List[Dict]:
        """
        Compare dealers for a specific model based on listings.

        Returns:
            List of dealer comparisons with average prices and ratings
        """
        dealer_stats: Dict[str, Dict] = {}

        for listing in listings:
            match = self.match_listing_to_dealer(listing, market_value)

            if match.detected_dealer:
                dealer_id = match.detected_dealer.name
                if dealer_id not in dealer_stats:
                    dealer_stats[dealer_id] = {
                        'dealer': match.detected_dealer,
                        'prices': [],
                        'avg_markup_pct': 0,
                        'count': 0,
                    }

                dealer_stats[dealer_id]['prices'].append(listing.get('price', 0))
                dealer_stats[dealer_id]['count'] += 1

        # Calculate averages
        results = []
        for dealer_id, stats in dealer_stats.items():
            if stats['prices']:
                avg_price = sum(stats['prices']) / len(stats['prices'])
                markup_pct = ((avg_price - market_value) / market_value * 100)
                stats['avg_price'] = avg_price
                stats['avg_markup_pct'] = markup_pct
                results.append(stats)

        # Sort by price (best deals first)
        return sorted(results, key=lambda x: x.get('avg_price', float('inf')))

    def identify_aggressive_dealers(
        self,
        listings: List[Dict],
        market_value: float,
        threshold_pct: float = 5.0,
    ) -> List[DealerProfile]:
        """Identify dealers consistently pricing below market."""
        dealer_deltas: Dict[str, List[float]] = {}

        for listing in listings:
            match = self.match_listing_to_dealer(listing, market_value)
            if match.detected_dealer:
                dealer_name = match.detected_dealer.name
                price_diff = listing.get('price', 0) - market_value
                if dealer_name not in dealer_deltas:
                    dealer_deltas[dealer_name] = []
                dealer_deltas[dealer_name].append(price_diff)

        aggressive = []
        for dealer_name, deltas in dealer_deltas.items():
            if deltas:
                avg_delta = sum(deltas) / len(deltas)
                avg_delta_pct = (avg_delta / market_value * 100)

                # If dealer is consistently underselling market
                if avg_delta_pct < -threshold_pct:
                    dealer = next(
                        (d for d in self.db.get_all_dealers() if d.name == dealer_name),
                        None,
                    )
                    if dealer:
                        aggressive.append(dealer)

        return sorted(aggressive, key=lambda d: d.average_markup_pct)


# Global instance
_matcher = None


def get_dealer_matcher() -> DealerMatcher:
    """Get global dealer matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = DealerMatcher()
    return _matcher
