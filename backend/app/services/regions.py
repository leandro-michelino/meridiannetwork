from dataclasses import dataclass

from app.config import Settings
from app.models import RegionSummary


OCI_REGIONS: tuple[tuple[str, str], ...] = (
    ("eu-frankfurt-1", "Europe"),
    ("eu-amsterdam-1", "Europe"),
    ("eu-london-1", "Europe"),
    ("eu-paris-1", "Europe"),
    ("eu-milan-1", "Europe"),
    ("eu-stockholm-1", "Europe"),
    ("eu-madrid-1", "Europe"),
    ("us-ashburn-1", "North America"),
    ("us-phoenix-1", "North America"),
    ("us-chicago-1", "North America"),
    ("ca-toronto-1", "North America"),
    ("af-johannesburg-1", "Africa"),
    ("me-dubai-1", "Middle East"),
    ("me-jeddah-1", "Middle East"),
    ("ap-tokyo-1", "Asia Pacific"),
    ("ap-singapore-1", "Asia Pacific"),
    ("ap-sydney-1", "Asia Pacific"),
    ("ap-mumbai-1", "Asia Pacific"),
    ("sa-saopaulo-1", "South America"),
    ("sa-vinhedo-1", "South America"),
)


@dataclass(frozen=True)
class RegionService:
    settings: Settings

    def list_available(self) -> list[RegionSummary]:
        active = set(self.settings.active_regions)
        return [
            RegionSummary(
                id=region_id,
                geo=geo,
                is_home_region=region_id == self.settings.home_region,
                is_active=region_id in active,
            )
            for region_id, geo in OCI_REGIONS
        ]

