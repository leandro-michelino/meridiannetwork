from dataclasses import dataclass

from app.config import Settings
from app.models import RegionSummary


OCI_REGIONS: tuple[tuple[str, str], ...] = (
    # North America
    ("us-ashburn-1", "North America"),
    ("us-phoenix-1", "North America"),
    ("us-chicago-1", "North America"),
    ("us-sanjose-1", "North America"),
    ("ca-toronto-1", "North America"),
    ("ca-montreal-1", "North America"),
    ("mx-queretaro-1", "North America"),
    ("mx-monterrey-1", "North America"),
    # Europe
    ("eu-frankfurt-1", "Europe"),
    ("eu-amsterdam-1", "Europe"),
    ("eu-london-1", "Europe"),
    ("eu-paris-1", "Europe"),
    ("eu-marseille-1", "Europe"),
    ("eu-milan-1", "Europe"),
    ("eu-stockholm-1", "Europe"),
    ("eu-madrid-1", "Europe"),
    ("eu-zurich-1", "Europe"),
    ("eu-jovanovac-1", "Europe"),
    # Middle East
    ("me-abudhabi-1", "Middle East"),
    ("me-dubai-1", "Middle East"),
    ("me-jeddah-1", "Middle East"),
    ("me-riyadh-1", "Middle East"),
    ("il-jerusalem-1", "Middle East"),
    # Asia Pacific
    ("ap-tokyo-1", "Asia Pacific"),
    ("ap-osaka-1", "Asia Pacific"),
    ("ap-singapore-1", "Asia Pacific"),
    ("ap-sydney-1", "Asia Pacific"),
    ("ap-melbourne-1", "Asia Pacific"),
    ("ap-mumbai-1", "Asia Pacific"),
    ("ap-hyderabad-1", "Asia Pacific"),
    ("ap-seoul-1", "Asia Pacific"),
    ("ap-chuncheon-1", "Asia Pacific"),
    ("ap-jakarta-1", "Asia Pacific"),
    # Africa
    ("af-johannesburg-1", "Africa"),
    # South America
    ("sa-saopaulo-1", "South America"),
    ("sa-vinhedo-1", "South America"),
    ("sa-bogota-1", "South America"),
    ("sa-santiago-1", "South America"),
)


@dataclass(frozen=True)
class RegionService:
    settings: Settings

    def list_available(self) -> list[RegionSummary]:
        active = {self.settings.home_region, *self.settings.active_regions}
        return [
            RegionSummary(
                id=region_id,
                geo=geo,
                is_home_region=region_id == self.settings.home_region,
                is_active=region_id in active,
            )
            for region_id, geo in OCI_REGIONS
        ]

    def list_active(self) -> list[RegionSummary]:
        return [r for r in self.list_available() if r.is_active]
