"""Data residency configuration and region management"""
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel


class DataRegion(str, Enum):
    """Supported data residency regions"""

    # US Regions
    US_EAST_1 = "us-east-1"  # US East (N. Virginia)
    US_EAST_2 = "us-east-2"  # US East (Ohio)
    US_WEST_1 = "us-west-1"  # US West (N. California)
    US_WEST_2 = "us-west-2"  # US West (Oregon)

    # Europe Regions
    EU_WEST_1 = "eu-west-1"  # Europe (Ireland)
    EU_WEST_2 = "eu-west-2"  # Europe (London)
    EU_CENTRAL_1 = "eu-central-1"  # Europe (Frankfurt)

    # Asia Pacific Regions
    AP_SOUTHEAST_1 = "ap-southeast-1"  # Asia Pacific (Singapore)
    AP_SOUTHEAST_2 = "ap-southeast-2"  # Asia Pacific (Sydney)
    AP_NORTHEAST_1 = "ap-northeast-1"  # Asia Pacific (Tokyo)
    AP_SOUTH_1 = "ap-south-1"  # Asia Pacific (Mumbai)

    # Canada
    CA_CENTRAL_1 = "ca-central-1"  # Canada (Central)

    # UK (for GDPR compliance)
    UK_SOUTH_1 = "uk-south-1"  # UK South


class RegionInfo(BaseModel):
    """Information about a data residency region"""
    code: str
    name: str
    country: str
    continent: str
    gdpr_compliant: bool = False
    hipaa_compliant: bool = False
    description: str
    storage_endpoint: Optional[str] = None
    database_endpoint: Optional[str] = None
    latency_zone: str  # low, medium, high


# Region metadata
REGION_INFO: Dict[str, RegionInfo] = {
    DataRegion.US_EAST_1: RegionInfo(
        code="us-east-1",
        name="US East (N. Virginia)",
        country="United States",
        continent="North America",
        gdpr_compliant=False,
        hipaa_compliant=True,
        description="Primary US region with lowest latency for East Coast",
        latency_zone="low",
    ),
    DataRegion.US_EAST_2: RegionInfo(
        code="us-east-2",
        name="US East (Ohio)",
        country="United States",
        continent="North America",
        gdpr_compliant=False,
        hipaa_compliant=True,
        description="Secondary US region with redundancy",
        latency_zone="low",
    ),
    DataRegion.US_WEST_1: RegionInfo(
        code="us-west-1",
        name="US West (N. California)",
        country="United States",
        continent="North America",
        gdpr_compliant=False,
        hipaa_compliant=True,
        description="West Coast US region",
        latency_zone="medium",
    ),
    DataRegion.US_WEST_2: RegionInfo(
        code="us-west-2",
        name="US West (Oregon)",
        country="United States",
        continent="North America",
        gdpr_compliant=False,
        hipaa_compliant=True,
        description="Pacific Northwest US region",
        latency_zone="medium",
    ),
    DataRegion.EU_WEST_1: RegionInfo(
        code="eu-west-1",
        name="Europe (Ireland)",
        country="Ireland",
        continent="Europe",
        gdpr_compliant=True,
        hipaa_compliant=False,
        description="Primary EU region with GDPR compliance",
        latency_zone="low",
    ),
    DataRegion.EU_WEST_2: RegionInfo(
        code="eu-west-2",
        name="Europe (London)",
        country="United Kingdom",
        continent="Europe",
        gdpr_compliant=True,
        hipaa_compliant=False,
        description="UK region with GDPR compliance",
        latency_zone="low",
    ),
    DataRegion.EU_CENTRAL_1: RegionInfo(
        code="eu-central-1",
        name="Europe (Frankfurt)",
        country="Germany",
        continent="Europe",
        gdpr_compliant=True,
        hipaa_compliant=False,
        description="Central EU region with GDPR compliance",
        latency_zone="medium",
    ),
    DataRegion.AP_SOUTHEAST_1: RegionInfo(
        code="ap-southeast-1",
        name="Asia Pacific (Singapore)",
        country="Singapore",
        continent="Asia",
        gdpr_compliant=False,
        hipaa_compliant=False,
        description="Southeast Asia region",
        latency_zone="high",
    ),
    DataRegion.AP_SOUTHEAST_2: RegionInfo(
        code="ap-southeast-2",
        name="Asia Pacific (Sydney)",
        country="Australia",
        continent="Oceania",
        gdpr_compliant=False,
        hipaa_compliant=False,
        description="Australia region",
        latency_zone="high",
    ),
    DataRegion.AP_NORTHEAST_1: RegionInfo(
        code="ap-northeast-1",
        name="Asia Pacific (Tokyo)",
        country="Japan",
        continent="Asia",
        gdpr_compliant=False,
        hipaa_compliant=False,
        description="Japan region",
        latency_zone="high",
    ),
    DataRegion.AP_SOUTH_1: RegionInfo(
        code="ap-south-1",
        name="Asia Pacific (Mumbai)",
        country="India",
        continent="Asia",
        gdpr_compliant=False,
        hipaa_compliant=False,
        description="India region",
        latency_zone="high",
    ),
    DataRegion.CA_CENTRAL_1: RegionInfo(
        code="ca-central-1",
        name="Canada (Central)",
        country="Canada",
        continent="North America",
        gdpr_compliant=False,
        hipaa_compliant=True,
        description="Canada region with data sovereignty compliance",
        latency_zone="medium",
    ),
    DataRegion.UK_SOUTH_1: RegionInfo(
        code="uk-south-1",
        name="UK South",
        country="United Kingdom",
        continent="Europe",
        gdpr_compliant=True,
        hipaa_compliant=False,
        description="UK region for data sovereignty",
        latency_zone="low",
    ),
}


class RegionService:
    """Service for managing data residency regions"""

    @staticmethod
    def get_region_info(region_code: str) -> Optional[RegionInfo]:
        """Get information about a region"""
        return REGION_INFO.get(region_code)

    @staticmethod
    def list_regions(
        gdpr_only: bool = False,
        hipaa_only: bool = False,
        continent: Optional[str] = None,
    ) -> List[RegionInfo]:
        """List available regions with optional filters"""
        regions = list(REGION_INFO.values())

        if gdpr_only:
            regions = [r for r in regions if r.gdpr_compliant]

        if hipaa_only:
            regions = [r for r in regions if r.hipaa_compliant]

        if continent:
            regions = [r for r in regions if r.continent.lower() == continent.lower()]

        return regions

    @staticmethod
    def is_valid_region(region_code: str) -> bool:
        """Check if a region code is valid"""
        return region_code in REGION_INFO

    @staticmethod
    def get_storage_endpoint(region_code: str) -> Optional[str]:
        """Get the storage endpoint for a region"""
        region = REGION_INFO.get(region_code)
        return region.storage_endpoint if region else None

    @staticmethod
    def get_database_endpoint(region_code: str) -> Optional[str]:
        """Get the database endpoint for a region"""
        region = REGION_INFO.get(region_code)
        return region.database_endpoint if region else None

    @staticmethod
    def validate_region_for_compliance(
        region_code: str,
        require_gdpr: bool = False,
        require_hipaa: bool = False,
    ) -> bool:
        """Validate that a region meets compliance requirements"""
        region = REGION_INFO.get(region_code)

        if not region:
            return False

        if require_gdpr and not region.gdpr_compliant:
            return False

        if require_hipaa and not region.hipaa_compliant:
            return False

        return True

    @staticmethod
    def get_default_region() -> str:
        """Get the default region (US East 1)"""
        return DataRegion.US_EAST_1.value

    @staticmethod
    def get_nearest_region(continent: str) -> str:
        """Get the recommended region for a continent"""
        continent_map = {
            "north america": DataRegion.US_EAST_1.value,
            "south america": DataRegion.US_EAST_1.value,
            "europe": DataRegion.EU_WEST_1.value,
            "asia": DataRegion.AP_SOUTHEAST_1.value,
            "africa": DataRegion.EU_WEST_1.value,
            "oceania": DataRegion.AP_SOUTHEAST_2.value,
        }

        return continent_map.get(continent.lower(), DataRegion.US_EAST_1.value)

    @staticmethod
    def get_gdpr_regions() -> List[str]:
        """Get list of GDPR-compliant regions"""
        return [
            region.code
            for region in REGION_INFO.values()
            if region.gdpr_compliant
        ]

    @staticmethod
    def get_hipaa_regions() -> List[str]:
        """Get list of HIPAA-compliant regions"""
        return [
            region.code
            for region in REGION_INFO.values()
            if region.hipaa_compliant
        ]

    @staticmethod
    def can_migrate_between_regions(
        source_region: str,
        target_region: str,
        require_same_compliance: bool = True,
    ) -> bool:
        """Check if data can be migrated between two regions

        Args:
            source_region: Source region code
            target_region: Target region code
            require_same_compliance: If True, regions must have same compliance status

        Returns:
            True if migration is allowed, False otherwise
        """
        source = REGION_INFO.get(source_region)
        target = REGION_INFO.get(target_region)

        if not source or not target:
            return False

        # Can't migrate from GDPR to non-GDPR region
        if source.gdpr_compliant and not target.gdpr_compliant:
            return False

        # Can't migrate from HIPAA to non-HIPAA region
        if source.hipaa_compliant and not target.hipaa_compliant:
            return False

        if require_same_compliance:
            if source.gdpr_compliant != target.gdpr_compliant:
                return False
            if source.hipaa_compliant != target.hipaa_compliant:
                return False

        return True
