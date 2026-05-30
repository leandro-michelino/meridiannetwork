from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .config import Settings


class OciClientError(RuntimeError):
    """Raised when OCI client setup or calls fail."""


OCI_CLIENT_TIMEOUT = (5, 15)


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
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.identity.IdentityClient(config=config, **kwargs)
        return oci.identity.IdentityClient(config, **kwargs)

    def virtual_network_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.core.VirtualNetworkClient(config=config, **kwargs)
        return oci.core.VirtualNetworkClient(config, **kwargs)

    def compute_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.core.ComputeClient(config=config, **kwargs)
        return oci.core.ComputeClient(config, **kwargs)

    def resource_search_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer, timeout=(3, 6))
        return oci.resource_search.ResourceSearchClient(config, **kwargs)

    def structured_search_details(self, query: str) -> Any:
        oci = self._load_oci()
        return oci.resource_search.models.StructuredSearchDetails(query=query, type="Structured")

    def object_storage_client(self) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config()
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.object_storage.ObjectStorageClient(config=config, **kwargs)
        return oci.object_storage.ObjectStorageClient(config, **kwargs)

    def logging_management_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.logging.LoggingManagementClient(config=config, **kwargs)
        return oci.logging.LoggingManagementClient(config, **kwargs)

    def logging_search_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer)
        if signer is not None:
            return oci.loggingsearch.LogSearchClient(config=config, **kwargs)
        return oci.loggingsearch.LogSearchClient(config, **kwargs)

    def vn_monitoring_client(self, region: str | None = None) -> Any:
        oci = self._load_oci()
        signer, config = self.signer_and_config(region=region)
        kwargs = self._client_kwargs(signer, timeout=(5, 10))
        return oci.vn_monitoring.VnMonitoringClient(config, **kwargs)

    def _client_kwargs(self, signer: Any | None, timeout: tuple[int, int] = OCI_CLIENT_TIMEOUT) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if signer is not None:
            kwargs["signer"] = signer
        return kwargs

    def logging_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.logging.models, name)(**kwargs)

    def core_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.core.models, name)(**kwargs)

    def loggingsearch_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.loggingsearch.models, name)(**kwargs)

    def vn_monitoring_model(self, name: str, **kwargs: Any) -> Any:
        oci = self._load_oci()
        return getattr(oci.vn_monitoring.models, name)(**kwargs)

    def list_all(self, list_func: Any, *args: Any, **kwargs: Any) -> list[Any]:
        oci = self._load_oci()
        return oci.pagination.list_call_get_all_results(list_func, *args, **kwargs).data
