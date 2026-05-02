from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from difflib import SequenceMatcher
import re


@dataclass
class MatchResult:
    """Result of matching a listing against hit list."""
    is_hit: bool
    hit_entry: Optional[Dict[str, Any]] = None
    match_confidence: float = 0.0
    model_match: str = ""
    year_match: bool = False
    steal_indicators_found: List[str] = None
    reasoning: str = ""

    def __post_init__(self):
        if self.steal_indicators_found is None:
            self.steal_indicators_found = []


class ListingMatcher:
    """Match listings against hit list criteria."""

    def __init__(self, hit_list_dict: Dict[str, Any]):
        """Initialize with hit list data."""
        self.hit_list = hit_list_dict

    def match_listing(self, listing: Dict[str, Any]) -> MatchResult:
        """
        Match a listing against hit list.
        Returns MatchResult with details about the match.
        """
        listing_model = listing.get('model', '').strip()
        listing_year = listing.get('year')
        listing_price = listing.get('price')

        if not listing_model or not listing_year:
            return MatchResult(
                is_hit=False,
                reasoning="Missing model or year information"
            )

        # Try to find matching hit list entry
        best_match = None
        best_confidence = 0.0

        for hit_key, hit_entry in self.hit_list.items():
            confidence = self._calculate_model_confidence(listing_model, hit_entry['model'])

            if confidence > best_confidence:
                # Check if year is in range
                year_start, year_end = hit_entry['year_range']
                if year_start <= listing_year <= year_end:
                    best_match = (hit_key, hit_entry)
                    best_confidence = confidence

        if not best_match:
            return MatchResult(
                is_hit=False,
                reasoning=f"No matching model found for '{listing_model}'"
            )

        hit_key, hit_entry = best_match
        listing_price_float = float(listing_price) if listing_price else 0.0
        target_price = hit_entry['target_price_value']

        # Check if price is within range
        if listing_price_float > target_price:
            return MatchResult(
                is_hit=False,
                hit_entry=hit_entry,
                model_match=hit_entry['model'],
                year_match=True,
                match_confidence=best_confidence,
                reasoning=f"Price ${listing_price_float:,.0f} exceeds target ${target_price:,.0f}"
            )

        # Check for steal indicators
        steal_indicators_found = self._extract_steal_indicators(
            listing,
            hit_entry['steal_indicator']
        )

        if not steal_indicators_found:
            return MatchResult(
                is_hit=False,
                hit_entry=hit_entry,
                model_match=hit_entry['model'],
                year_match=True,
                match_confidence=best_confidence,
                reasoning=f"Price matches but missing key steal indicator: {hit_entry['steal_indicator']}"
            )

        # This is a hit!
        savings = target_price - listing_price_float
        reasoning = (
            f"✓ {hit_entry['model']} {hit_entry['generation']} "
            f"({listing_year}) at ${listing_price_float:,.0f} "
            f"- Save ${savings:,.0f} from target\n"
            f"✓ Steal indicators: {', '.join(steal_indicators_found)}"
        )

        return MatchResult(
            is_hit=True,
            hit_entry=hit_entry,
            model_match=hit_entry['model'],
            year_match=True,
            match_confidence=best_confidence,
            steal_indicators_found=steal_indicators_found,
            reasoning=reasoning
        )

    def _calculate_model_confidence(self, listing_model: str, hit_model: str) -> float:
        """
        Calculate confidence score for model match (0.0 to 1.0).
        Uses fuzzy string matching.
        """
        listing_lower = listing_model.lower().strip()
        hit_lower = hit_model.lower().strip()

        # Exact match
        if listing_lower == hit_lower:
            return 1.0

        # Partial match
        if hit_lower in listing_lower or listing_lower in hit_lower:
            return 0.8

        # Fuzzy match
        ratio = SequenceMatcher(None, listing_lower, hit_lower).ratio()
        return ratio if ratio > 0.6 else 0.0

    def _extract_steal_indicators(self, listing: Dict[str, Any], steal_indicator_desc: str) -> List[str]:
        """
        Extract steal indicators from listing based on description.
        Example: "Documented G6 engine swap + PCCBs"
        """
        found = []
        listing_text = self._prepare_listing_text(listing)

        # Parse steal indicator description (split by +)
        indicators = [ind.strip() for ind in steal_indicator_desc.split('+')]

        for indicator in indicators:
            if not indicator:
                continue

            # Check for exact and fuzzy matches in listing
            if self._indicator_present(indicator, listing_text):
                found.append(indicator)

        return found

    def _prepare_listing_text(self, listing: Dict[str, Any]) -> str:
        """Prepare listing text for search by combining key fields."""
        text_parts = [
            str(listing.get('title', '')).lower(),
            str(listing.get('condition', '')).lower(),
            str(listing.get('features_json', {})).lower(),
            str(listing.get('transmission', '')).lower(),
        ]
        return ' '.join(text_parts)

    def _indicator_present(self, indicator: str, listing_text: str) -> bool:
        """Check if indicator is present in listing text."""
        indicator_lower = indicator.lower()

        # Direct substring match
        if indicator_lower in listing_text:
            return True

        # Check common variations
        variations = self._get_indicator_variations(indicator_lower)
        for variation in variations:
            if variation in listing_text:
                return True

        return False

    @staticmethod
    def _get_indicator_variations(indicator: str) -> List[str]:
        """Get common spelling variations for an indicator."""
        variations = []

        # Common abbreviations and variations
        mapping = {
            'pccb': ['pccb', 'pcb', 'carbon ceramic brake', 'ceramic brake', 'carbon brake'],
            'carbon': ['carbon', 'cf'],
            'bucket': ['bucket', 'buckets', 'race bucket', 'sport bucket', 'oem bucket'],
            'weissach': ['weissach', 'weissach package'],
            'engine swap': ['engine swap', 'g6 engine', 'engine replacement'],
            'manual': ['manual', 'manual transmission', 'manual gearbox'],
            'chrono': ['chrono', 'sport chrono', 'chrono package'],
            'lift': ['front-axle lift', 'axle lift', 'lift'],
        }

        indicator_lower = indicator.lower()
        for key, vars_list in mapping.items():
            if key in indicator_lower:
                variations.extend(vars_list)

        # If no specific mapping, add the indicator itself
        if not variations:
            variations.append(indicator_lower)

        return variations
