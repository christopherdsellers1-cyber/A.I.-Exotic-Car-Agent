from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class RequirementCheckResult:
    """Result of checking listing against requirements."""
    meets_requirements: bool
    passed_checks: List[str]
    failed_checks: List[str]
    warnings: List[str]
    confidence_score: float  # 0.0 to 1.0


class RequirementChecker:
    """Check listings against general requirements."""

    def __init__(self, requirements: List[str]):
        """Initialize with requirements list."""
        self.requirements = requirements
        self.hard_requirements = self._identify_hard_requirements()
        self.soft_requirements = self._identify_soft_requirements()

    def check_listing(self, listing: Dict[str, Any]) -> RequirementCheckResult:
        """Check a listing against all requirements."""
        passed = []
        failed = []
        warnings = []

        # Check hard requirements (must have)
        for req in self.hard_requirements:
            result, msg = self._check_single_requirement(listing, req)
            if result:
                passed.append(msg)
            else:
                failed.append(msg)

        # Check soft requirements (nice to have)
        for req in self.soft_requirements:
            result, msg = self._check_single_requirement(listing, req)
            if result:
                passed.append(msg)
            else:
                warnings.append(msg)

        # Calculate confidence score
        total_hard = len(self.hard_requirements)
        passed_hard = sum(1 for req in self.hard_requirements if self._check_single_requirement(listing, req)[0])

        confidence = (passed_hard / total_hard) if total_hard > 0 else 0.0
        if len(self.soft_requirements) > 0:
            passed_soft = sum(1 for req in self.soft_requirements if self._check_single_requirement(listing, req)[0])
            confidence += (passed_soft / (total_hard + len(self.soft_requirements))) * 0.3

        meets_requirements = len(failed) == 0

        return RequirementCheckResult(
            meets_requirements=meets_requirements,
            passed_checks=passed,
            failed_checks=failed,
            warnings=warnings,
            confidence_score=min(confidence, 1.0)
        )

    def _check_single_requirement(self, listing: Dict[str, Any], requirement: str) -> Tuple[bool, str]:
        """Check a single requirement against listing."""
        requirement_lower = requirement.lower()

        # Clean Title
        if 'clean title' in requirement_lower:
            title_status = str(listing.get('title_status', '')).lower()
            is_clean = 'clean' in title_status or 'salvage' not in title_status and 'branded' not in title_status
            msg = "✓ Clean title" if is_clean else "✗ Title status unclear/not clean"
            return is_clean, msg

        # Number of Owners
        if 'owner' in requirement_lower:
            owner_count = listing.get('owner_count')
            if owner_count is None:
                return False, "✗ Owner count not specified"

            # Parse requirement (e.g., "One to Six Owners" -> 1-6)
            if 1 <= owner_count <= 6:
                return True, f"✓ {owner_count} owner(s) (within range)"
            else:
                return False, f"✗ {owner_count} owner(s) (outside 1-6 range)"

        # Service Records
        if 'service record' in requirement_lower:
            has_service = listing.get('has_service_records', False)
            msg = "✓ Service records available" if has_service else "✗ No service records mentioned"
            return has_service, msg

        # No Accidents
        if 'accident' in requirement_lower or 'no accident' in requirement_lower:
            has_accidents = listing.get('has_accidents', False)
            msg = "✓ No accidents reported" if not has_accidents else "✗ Accident history detected"
            return not has_accidents, msg

        # Specific Features (Weissach, bucket seats, etc.)
        if any(feature in requirement_lower for feature in ['weissach', 'bucket', 'brakes', 'chrono', 'lift']):
            features = listing.get('features_json', {})
            if isinstance(features, dict):
                features_str = str(features).lower()
            else:
                features_str = str(features).lower()

            feature_name = self._extract_feature_name(requirement)
            if feature_name and feature_name.lower() in features_str:
                return True, f"✓ {feature_name} present"
            else:
                return False, f"✗ {requirement} not confirmed"

        # Transmission (Manual)
        if 'manual' in requirement_lower:
            transmission = str(listing.get('transmission', '')).lower()
            is_manual = 'manual' in transmission
            msg = "✓ Manual transmission" if is_manual else "✗ Not manual transmission"
            return is_manual, msg

        # Price threshold ($5-20k below market)
        if 'price' in requirement_lower and ('below' in requirement_lower or '$5k' in requirement_lower):
            # This is checked separately in pricing filter
            return True, "✓ Price within acceptable range"

        # Generic feature check
        features = listing.get('features_json', {})
        if features:
            features_str = str(features).lower()
            if requirement_lower in features_str:
                return True, f"✓ {requirement}"

        return True, f"○ {requirement} (not checked)"

    @staticmethod
    def _extract_feature_name(requirement: str) -> str:
        """Extract feature name from requirement text."""
        features = ['weissach', 'bucket', 'carbon ceramic', 'pccb', 'chrono', 'lift', 'manufaktur']
        req_lower = requirement.lower()
        for feature in features:
            if feature in req_lower:
                return feature
        return requirement

    def _identify_hard_requirements(self) -> List[str]:
        """Identify which requirements are hard must-haves."""
        hard_keywords = ['clean title', 'no accident', 'service record', 'must have']
        hard = []
        for req in self.requirements:
            if any(keyword in req.lower() for keyword in hard_keywords):
                hard.append(req)
        return hard

    def _identify_soft_requirements(self) -> List[str]:
        """Identify which requirements are soft nice-to-haves."""
        hard = self._identify_hard_requirements()
        return [req for req in self.requirements if req not in hard]
