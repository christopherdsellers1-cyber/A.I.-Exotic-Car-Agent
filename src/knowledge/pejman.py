"""
Knowledge Base Module - Pejman AI Features
Intelligent analysis and decision-making for Porsche listing matching.
Named after Pejman Pahlavan - expert in automotive intelligence.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class VehicleKnowledge:
    """Expert knowledge about Porsche models."""
    model: str
    generation: str
    years: Tuple[int, int]
    market_value_range: Tuple[float, float]
    common_issues: List[str]
    desirable_features: List[str]
    depreciation_rate: float
    reliability_score: float


class PejmanKnowledgeBase:
    """
    AI-powered knowledge base for Porsche expertise.
    Provides intelligent matching and valuation analysis.
    """

    def __init__(self):
        self.logger_name = "pejman_knowledge"
        self._initialize_porsche_knowledge()

    def _initialize_porsche_knowledge(self):
        """Initialize expert knowledge about target Porsche models."""
        self.knowledge = {
            '991.1_GT3': VehicleKnowledge(
                model='Porsche 911 GT3',
                generation='991.1',
                years=(2014, 2016),
                market_value_range=(135000, 155000),
                common_issues=['IMS bearing wear', 'clutch wear on high-mileage units'],
                desirable_features=['documented service records', 'G6 engine swap', 'PCCB brakes', 'manual transmission'],
                depreciation_rate=0.08,
                reliability_score=0.85,
            ),
            '991.2_GT3': VehicleKnowledge(
                model='Porsche 911 GT3',
                generation='991.2',
                years=(2017, 2019),
                market_value_range=(175000, 220000),
                common_issues=['none known', 'generally reliable'],
                desirable_features=['manual transmission', 'bucket seats', 'PTS paint', 'low mileage'],
                depreciation_rate=0.06,
                reliability_score=0.92,
            ),
            '997.1_GT3_RS': VehicleKnowledge(
                model='Porsche 911 GT3 RS',
                generation='997.1',
                years=(2008, 2008),
                market_value_range=(220000, 280000),
                common_issues=['high mileage common', 'engine reliability depends on maintenance'],
                desirable_features=['low mileage', 'orange or green paint', 'clean service history', 'original owner'],
                depreciation_rate=0.04,
                reliability_score=0.80,
            ),
            '991.2_GT2_RS': VehicleKnowledge(
                model='Porsche 911 GT2 RS',
                generation='991.2',
                years=(2018, 2019),
                market_value_range=(420000, 500000),
                common_issues=['turbo maintenance critical', 'carbon buildup'],
                desirable_features=['Weissach package', 'magnesium wheels', 'low mileage', 'full service history'],
                depreciation_rate=0.05,
                reliability_score=0.88,
            ),
            '992.1_GT3_Touring': VehicleKnowledge(
                model='Porsche 911 GT3 Touring',
                generation='992.1',
                years=(2022, 2024),
                market_value_range=(200000, 250000),
                common_issues=['very new - no issues reported'],
                desirable_features=['PTS paint', 'manual transmission', 'at or near MSRP', 'warranty remaining'],
                depreciation_rate=0.10,
                reliability_score=0.98,
            ),
            '992.1_GT3_RS': VehicleKnowledge(
                model='Porsche 911 GT3 RS',
                generation='992.1',
                years=(2023, 2024),
                market_value_range=(300000, 350000),
                common_issues=['very new - no issues'],
                desirable_features=['clean title', 'at or near MSRP', 'warranty', 'low mileage'],
                depreciation_rate=0.12,
                reliability_score=0.99,
            ),
        }

    def analyze_listing(self, model: str, generation: str, price: float, mileage: int, year: int) -> Dict:
        """
        Analyze a listing using expert knowledge.

        Returns:
            Dict with analysis results including value assessment and recommendations.
        """
        key = f"{generation}_{model.replace(' ', '_').replace('/', '')}"
        knowledge = self.knowledge.get(key)

        if not knowledge:
            return {'analysis': 'Unknown model', 'confidence': 0.0}

        # Value analysis
        market_low, market_high = knowledge.market_value_range
        market_mid = (market_low + market_high) / 2
        value_diff = market_mid - price
        value_pct = (value_diff / market_mid) * 100

        # Age and mileage analysis
        vehicle_age = 2026 - year
        expected_mileage = vehicle_age * 12000  # ~12k miles per year is average
        mileage_ratio = mileage / expected_mileage if expected_mileage > 0 else 1.0

        # Determine deal quality
        if value_pct >= 10:
            deal_quality = "EXCELLENT DEAL"
        elif value_pct >= 5:
            deal_quality = "GOOD DEAL"
        elif value_pct >= 0:
            deal_quality = "FAIR PRICE"
        else:
            deal_quality = "OVERPRICED"

        return {
            'model': knowledge.model,
            'generation': knowledge.generation,
            'market_value': market_mid,
            'price': price,
            'value_difference': value_diff,
            'value_percentage': value_pct,
            'deal_quality': deal_quality,
            'mileage_assessment': 'low' if mileage_ratio < 0.8 else 'normal' if mileage_ratio < 1.2 else 'high',
            'reliability_score': knowledge.reliability_score,
            'depreciation_rate': knowledge.depreciation_rate,
            'common_issues': knowledge.common_issues,
            'desirable_features': knowledge.desirable_features,
            'recommendation': self._generate_recommendation(deal_quality, mileage_ratio, knowledge.reliability_score),
        }

    def _generate_recommendation(self, deal_quality: str, mileage_ratio: float, reliability: float) -> str:
        """Generate expert recommendation."""
        if deal_quality == "EXCELLENT DEAL" and mileage_ratio < 1.2 and reliability > 0.85:
            return "🎯 STRONG BUY - Exceptional value"
        elif deal_quality == "GOOD DEAL" and reliability > 0.85:
            return "👍 BUY - Good opportunity"
        elif deal_quality == "FAIR PRICE" and mileage_ratio < 1.0:
            return "⚖️  FAIR - Reasonable for market"
        elif mileage_ratio > 1.5:
            return "⚠️  HIGH MILEAGE - Negotiate further"
        elif deal_quality == "OVERPRICED":
            return "❌ PASS - Asking too much"
        else:
            return "📊 EVALUATE - Need more information"

    def get_model_expertise(self, model: str, generation: str) -> Optional[VehicleKnowledge]:
        """Get expert knowledge about a specific model."""
        key = f"{generation}_{model.replace(' ', '_').replace('/', '')}"
        return self.knowledge.get(key)

    def compare_listings(self, listings: List[Dict]) -> List[Dict]:
        """
        Compare multiple listings and rank by value.

        Args:
            listings: List of listing dicts with model, generation, price, mileage, year

        Returns:
            Ranked list with analysis for each
        """
        analyses = []
        for listing in listings:
            analysis = self.analyze_listing(
                listing.get('model'),
                listing.get('generation'),
                listing.get('price'),
                listing.get('mileage', 0),
                listing.get('year'),
            )
            analysis['listing'] = listing
            analyses.append(analysis)

        # Sort by value percentage (best deals first)
        return sorted(analyses, key=lambda x: x.get('value_percentage', 0), reverse=True)


# Global knowledge base instance
_pejman = None


def get_pejman() -> PejmanKnowledgeBase:
    """Get global Pejman knowledge base instance."""
    global _pejman
    if _pejman is None:
        _pejman = PejmanKnowledgeBase()
    return _pejman
