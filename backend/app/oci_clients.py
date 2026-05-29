from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .config import Settings


class OciClientError(RuntimeError):
    """Raised when OCI client setup or calls fail."""


@dataclass(frozen=True)
class OciClientFactory:
    settings: Settings
    _signer_cache: Any | None = field(default=None, init=False, repr=False)

    def _load_oci(self) -> Any:
        try:
            import oci  # type: ignore[import-not-found]
        except ImportError as exc:
            raise OciClientError("OCI SDK is not installed.") from exc
        return oci

    def signer_and_config(self, region: str | None = None) -> tuple[Any | None, dict[str, Any]]:
        oci = self._load_oci()
        selected_region = region or self.settings.home_region

        if self.settings.oci_auth == "instance_principal":
            signer = self._signer_cache
            if signer is None:
                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                object.__setattr__(self, "_signer_cache", signer)
            return signer, {"region": selected_region}

        if self.settings.oci_auth == "resource_principal":
            signer = self._signer_cache
            if signer is None:
                signer = oci.auth.signers.get_resource_principals_signer()
                object.__setattr__(self, "_signer_cache", signer)
            return signer, {"region": selected_region}

        config = oci.config.from_file(profile_name=self.settings.oci_profile)
        if selected_region:
            config["region"] = selected_region
        return None, config

    def identity_client(self) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config()
        if signer is not None:
            return oci.identity.IdentityClient(config=config, signer=signer)
        return oci.identity.IdentityClient(config)

    def virtual_network_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        if signer is not None:
            return oci.core.VirtualNetworkClient(config=config, signer=signer)
        return oci.core.VirtualNetworkClient(config)

    def compute_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        if signer is not None:
            return oci.core.ComputeClient(config=config, signer=signer)
        return oci.core.ComputeClient(config)

    def resource_search_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs: dict[str, Any] = {"timeout": (3, 6)}
        if signer is not None:
            kwargs["signer"] = signer
        return oci.resource_search.ResourceSearchClient(config, **kwargs)

    def structured_search_details(self, query: str) -> Any:
        oci = self._load_oci()
        return oci.resource_search.models.StructuredSearchDetails(query=query, type="Structured")

    def object_storage_client(self) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config()
        if signer is not None:
            return oci.object_storage.ObjectStorageClient(config=config, signer=signer)
        return oci.object_storage.ObjectStorageClient(config)

    def logging_management_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        if signer is not None:
            return oci.logging.LoggingManagementClient(config=config, signer=signer)
        return oci.logging.LoggingManagementClient(config)

    def logging_search_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        if signer is not None:
            return oci.loggingsearch.LogSearchClient(config=config, signer=signer)
        return oci.loggingsearch.LogSearchClient(config)

    def logging_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.logging.models, name)(**kwargs)

    def core_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.core.models, name)(**kwargs)

    def loggingsearch_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.loggingsearch.models, name)(**kwargs)

    def list_all(self, list_func: Any, *args: Any, **kwargs: Any) -> list[Any]:
        oci = self._load_oci()
        return oci.pagination.list_call_get_all_results(list_func, *args, **kwargs).data
