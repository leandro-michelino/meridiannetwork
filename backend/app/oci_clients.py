from dataclasses import dataclass
from typing import Any

from .config import Settings


class OciClientError(RuntimeError):
    """Raised when OCI client setup or calls fail."""


@dataclass(frozen=True)
class OciClientFactory:
    settings: Settings

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
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            return signer, {"region": selected_region}

        if self.settings.oci_auth == "resource_principal":
            signer = oci.auth.signers.get_resource_principals_signer()
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

    def list_all(self, list_func: Any, *args: Any, **kwargs: Any) -> list[Any]:
        oci = self._load_oci()
        return oci.pagination.list_call_get_all_results(list_func, *args, **kwargs).data
