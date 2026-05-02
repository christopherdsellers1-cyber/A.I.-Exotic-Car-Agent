import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class HitListEntry:
    """Represents a single entry in hit_list.csv"""
    model: str
    generation: str
    years: str  # e.g., "2014-2016"
    target_buy_price: str  # e.g., "<$145,000"
    steal_indicator: str

    @property
    def year_range(self) -> tuple:
        """Parse year range into (start, end) tuple."""
        # Handle formats like "2014-2016", "2008", "2022+", "2023+"
        if '+' in self.years:
            # Format: "2022+" means 2022 to current/future
            year = int(self.years.replace('+', ''))
            return (year, 2030)  # Use 2030 as upper bound
        elif '-' in self.years:
            # Format: "2014-2016"
            parts = self.years.split('-')
            return (int(parts[0]), int(parts[1]))
        else:
            # Single year
            year = int(self.years)
            return (year, year)

    @property
    def target_price_value(self) -> float:
        """Extract numeric price value."""
        clean = self.target_buy_price.replace('$', '').replace(',', '').strip('<>= ')
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def __repr__(self):
        return f"<HitListEntry({self.model} {self.generation} {self.years} @ {self.target_buy_price})>"


class HitListParser:
    """Parse and manage hit_list.csv data."""

    @staticmethod
    def load(filepath: str) -> List[HitListEntry]:
        """Load hit_list.csv and return as list of HitListEntry objects."""
        entries = []
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Hit list file not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Model'):  # Skip empty rows
                    entry = HitListEntry(
                        model=row.get('Model', '').strip(),
                        generation=row.get('Generation', '').strip(),
                        years=row.get('Years', '').strip(),
                        target_buy_price=row.get('Target Buy Price', '').strip(),
                        steal_indicator=row.get('The Steal Indicator', '').strip()
                    )
                    entries.append(entry)

        return entries

    @staticmethod
    def to_dict(entries: List[HitListEntry]) -> Dict[str, Any]:
        """Convert entries to dictionary for easier lookup."""
        result = {}
        for entry in entries:
            key = f"{entry.generation}_{entry.model.replace(' ', '_')}"
            result[key] = {
                'model': entry.model,
                'generation': entry.generation,
                'years': entry.years,
                'year_range': entry.year_range,
                'target_buy_price': entry.target_buy_price,
                'target_price_value': entry.target_price_value,
                'steal_indicator': entry.steal_indicator,
            }
        return result


class RequirementsParser:
    """Parse and manage requirements.md data."""

    @staticmethod
    def load(filepath: str) -> List[str]:
        """Load requirements.md and return as list of requirement strings."""
        requirements = []
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Requirements file not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    requirements.append(line)

        return requirements

    @staticmethod
    def categorize(requirements: List[str]) -> Dict[str, List[str]]:
        """Categorize requirements into logical groups."""
        categories = {
            'title': [],
            'ownership': [],
            'features': [],
            'condition': [],
            'pricing': [],
            'transmission': [],
            'other': []
        }

        keywords = {
            'title': ['clean title', 'title'],
            'ownership': ['owner', 'owners'],
            'features': ['package', 'brakes', 'bucket', 'seat', 'lift', 'chrono', 'weissach', 'pccb', 'carbon', 'manufaktur'],
            'condition': ['accident', 'service record', 'records', 'condition'],
            'pricing': ['price', 'alert', 'below', 'market'],
            'transmission': ['manual', 'transmission', 'pdk'],
        }

        for req in requirements:
            req_lower = req.lower()
            categorized = False

            for category, keywords_list in keywords.items():
                if any(kw in req_lower for kw in keywords_list):
                    categories[category].append(req)
                    categorized = True
                    break

            if not categorized:
                categories['other'].append(req)

        return categories


def load_config(hit_list_path: str, requirements_path: str) -> Dict[str, Any]:
    """Load both hit list and requirements, return combined config."""
    hit_list = HitListParser.load(hit_list_path)
    requirements = RequirementsParser.load(requirements_path)

    return {
        'hit_list': hit_list,
        'hit_list_dict': HitListParser.to_dict(hit_list),
        'requirements': requirements,
        'requirements_categorized': RequirementsParser.categorize(requirements),
    }
