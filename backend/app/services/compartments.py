from __future__ import annotations
from dataclasses import dataclass

from app.config import Settings
from app.models import CompartmentSummary
from app.oci_clients import OciClientFactory, OciClientError


@dataclass(frozen=True)
class CompartmentService:
    settings: Settings
    client_factory: OciClientFactory

    def list_compartments(self) -> list[CompartmentSummary]:
        if not self.settings.enable_live_oci:
            return self._configured_compartments()

        if not self.settings.tenancy_ocid:
            raise OciClientError("MERIDIAN_TENANCY_OCID is required when live OCI calls are enabled.")

        client = self.client_factory.identity_client()
        compartments = self.client_factory.list_all(
            client.list_compartments,
            compartment_id=self.settings.tenancy_ocid,
            compartment_id_in_subtree=True,
            access_level="ACCESSIBLE",
        )

        results = [
            CompartmentSummary(
                id=self.settings.tenancy_ocid,
                name="tenancy-root",
                description="Root tenancy compartment",
                lifecycle_state="ACTIVE",
                parent_compartment_id=None,
                source="configured",
            )
        ]

        for item in compartments:
            results.append(
                CompartmentSummary(
                    id=item.id,
                    name=item.name,
                    description=item.description,
                    lifecycle_state=item.lifecycle_state,
                    parent_compartment_id=item.compartment_id,
                    source="oci",
                )
            )
        return results

    def _configured_compartments(self) -> list[CompartmentSummary]:
        results: list[CompartmentSummary] = []
        if not self.settings.tenancy_ocid:
            return [
                CompartmentSummary(
                    id=compartment_id,
                    name=compartment_id,
                    description="Configured monitored compartment. Enable live OCI calls to resolve its name.",
                    lifecycle_state="UNKNOWN",
                    parent_compartment_id=None,
                    source="configured",
                )
                for compartment_id in self.settings.compartment_ids
            ]

        results.append(
            CompartmentSummary(
                id=self.settings.tenancy_ocid,
                name="tenancy-root",
                description="Configured tenancy OCID. Enable live OCI calls to list child compartments.",
                lifecycle_state="UNKNOWN",
                parent_compartment_id=None,
                source="configured",
            )
        )
        for compartment_id in self.settings.compartment_ids:
            if compartment_id == self.settings.tenancy_ocid:
                continue
            results.append(
                CompartmentSummary(
                    id=compartment_id,
                    name=compartment_id,
                    description="Configured monitored compartment. Enable live OCI calls to resolve its name.",
                    lifecycle_state="UNKNOWN",
                    parent_compartment_id=self.settings.tenancy_ocid,
                    source="configured",
                )
            )
        return results
