"""
Test listing matching against hit list criteria.
"""

from src.filters.matcher import ListingMatcher
from src.parsers.common_schema import CommonListing


def test_gt3_match():
    """Test matching a 991.1 GT3 at steal price"""
    hit_list = {
        '991.1_GT3': {
            'model': 'Porsche GT3',
            'generation': '991.1',
            'years': '2014-2016',
            'year_range': (2014, 2016),
            'target_buy_price': '<$145,000',
            'target_price_value': 145000.0,
            'steal_indicator': 'Documented G6 engine swap + PCCBs',
        }
    }

    matcher = ListingMatcher(hit_list)

    # Create a test listing
    listing = {
        'model': 'Porsche 911 GT3',
        'year': 2015,
        'price': 142000,
        'title': '2015 Porsche 911 GT3 - Documented G6 engine swap with PCCBs',
        'features_json': {'engine': 'G6 swap', 'brakes': 'carbon ceramic PCCB'},
        'transmission': 'Manual',
        'condition': 'Excellent',
    }

    result = matcher.match_listing(listing)

    assert result.is_hit, f"Should be a hit: {result.reasoning}"
    assert result.hit_entry is not None, "Should have hit entry"
    assert len(result.steal_indicators_found) > 0, "Should find steal indicators"
    print(f"✓ Test passed: {result.reasoning}")


def test_gt3_above_price():
    """Test GT3 above target price (no hit)"""
    hit_list = {
        '991.1_GT3': {
            'model': 'Porsche GT3',
            'generation': '991.1',
            'years': '2014-2016',
            'year_range': (2014, 2016),
            'target_buy_price': '<$145,000',
            'target_price_value': 145000.0,
            'steal_indicator': 'Documented G6 engine swap',
        }
    }

    matcher = ListingMatcher(hit_list)

    listing = {
        'model': 'Porsche 911 GT3',
        'year': 2015,
        'price': 155000,  # Above target
        'title': '2015 Porsche 911 GT3',
        'features_json': {},
    }

    result = matcher.match_listing(listing)

    assert not result.is_hit, "Should not be a hit (above price)"
    print(f"✓ Test passed: {result.reasoning}")


def test_gt3_missing_steal_indicator():
    """Test GT3 at good price but missing steal indicator"""
    hit_list = {
        '991.1_GT3': {
            'model': 'Porsche GT3',
            'generation': '991.1',
            'years': '2014-2016',
            'year_range': (2014, 2016),
            'target_buy_price': '<$145,000',
            'target_price_value': 145000.0,
            'steal_indicator': 'Documented G6 engine swap + PCCBs',
        }
    }

    matcher = ListingMatcher(hit_list)

    listing = {
        'model': 'Porsche 911 GT3',
        'year': 2015,
        'price': 142000,
        'title': '2015 Porsche 911 GT3 - Stock engine',
        'features_json': {'brakes': 'ceramic'},
    }

    result = matcher.match_listing(listing)

    assert not result.is_hit, "Should not be a hit (missing steal indicator)"
    print(f"✓ Test passed: {result.reasoning}")


def test_no_matching_model():
    """Test listing with no matching model in hit list"""
    hit_list = {
        '991.1_GT3': {
            'model': 'Porsche GT3',
            'generation': '991.1',
            'years': '2014-2016',
            'year_range': (2014, 2016),
            'target_buy_price': '<$145,000',
            'target_price_value': 145000.0,
            'steal_indicator': 'Documented G6 engine swap',
        }
    }

    matcher = ListingMatcher(hit_list)

    listing = {
        'model': 'Porsche Cayman S',  # Not in hit list
        'year': 2015,
        'price': 42000,
        'title': '2015 Porsche Cayman S',
        'features_json': {},
    }

    result = matcher.match_listing(listing)

    assert not result.is_hit, "Should not match non-target model"
    print(f"✓ Test passed: {result.reasoning}")


if __name__ == '__main__':
    test_gt3_match()
    test_gt3_above_price()
    test_gt3_missing_steal_indicator()
    test_no_matching_model()
    print("\n✓ All matcher tests passed!")
