from __future__ import annotations
from dataclasses import dataclass

from app.config import Settings
from app.models import RegionSummary
from app.oci_clients import OciClientFactory


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
    client_factory: OciClientFactory | None = None

    def list_available(self) -> list[RegionSummary]:
        subscribed = self._subscribed_regions()
        if subscribed:
            return subscribed

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

    def _subscribed_regions(self) -> list[RegionSummary]:
        if not self.settings.enable_live_oci or not self.settings.tenancy_ocid or self.client_factory is None:
            return []

        try:
            client = self.client_factory.identity_client()
            subscriptions = self.client_factory.list_all(
                client.list_region_subscriptions,
                self.settings.tenancy_ocid,
            )
        except Exception:
            return []
        regions = [
            RegionSummary(
                id=str(item.region_name),
                geo=self._region_geo(str(item.region_name)),
                is_home_region=bool(getattr(item, "is_home_region", False)),
                is_active=str(getattr(item, "status", "READY")).upper() == "READY",
            )
            for item in subscriptions
            if getattr(item, "region_name", None)
        ]
        return sorted(regions, key=lambda item: (not item.is_home_region, item.id))

    def _region_geo(self, region_id: str) -> str:
        known = dict(OCI_REGIONS)
        if region_id in known:
            return known[region_id]
        if region_id.startswith("eu-") or region_id.startswith("uk-"):
            return "Europe"
        if region_id.startswith(("us-", "ca-", "mx-")):
            return "North America"
        if region_id.startswith("af-"):
            return "Africa"
        if region_id.startswith(("me-", "il-")):
            return "Middle East"
        if region_id.startswith("ap-"):
            return "Asia Pacific"
        if region_id.startswith("sa-"):
            return "South America"
        return "Region"
