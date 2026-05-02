"""
Test configuration and CSV loading.
"""

import pytest
from pathlib import Path
from src.utils.csv_parser import HitListParser, RequirementsParser, load_config
from src.config import get_config


def test_hit_list_loading():
    """Test loading hit_list.csv"""
    config_dir = Path(__file__).parent.parent / "data"
    hit_list_path = config_dir / "hit_list.csv"

    if hit_list_path.exists():
        entries = HitListParser.load(str(hit_list_path))
        assert len(entries) > 0, "Should load hit list entries"
        assert entries[0].model is not None, "Should have model"
        assert entries[0].year_range is not None, "Should have year range"
        print(f"✓ Loaded {len(entries)} hit list entries")


def test_requirements_loading():
    """Test loading requirements.md"""
    config_dir = Path(__file__).parent.parent / "data"
    requirements_path = config_dir / "requirements.md"

    if requirements_path.exists():
        requirements = RequirementsParser.load(str(requirements_path))
        assert len(requirements) > 0, "Should load requirements"
        print(f"✓ Loaded {len(requirements)} requirements")

        # Test categorization
        categorized = RequirementsParser.categorize(requirements)
        assert len(categorized) > 0, "Should categorize requirements"
        print(f"✓ Categorized into {len(categorized)} categories")


def test_config_initialization():
    """Test config loading"""
    config = get_config()
    assert config is not None, "Should initialize config"
    assert len(config.hit_list) > 0, "Should load hit list"
    assert len(config.requirements) > 0, "Should load requirements"
    print(f"✓ Config loaded: {config}")


if __name__ == '__main__':
    test_hit_list_loading()
    test_requirements_loading()
    test_config_initialization()
    print("\n✓ All configuration tests passed!")
