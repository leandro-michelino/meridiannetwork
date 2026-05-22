from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import IdentityContext

router = APIRouter(prefix="/api/identity", tags=["identity"])


@router.get("/context", response_model=IdentityContext)
def identity_context(settings: Settings = Depends(get_settings)) -> IdentityContext:
    """Return the current IAM identity context.

    Full OCI IAM Domain integration is planned. Until then this endpoint
    returns a static response that tells the dashboard to fall back to
    manual user entry for security action attribution.
    """
    return IdentityContext(
        enabled=False,
        source="manual",
        domain_name="Default",
        current_user=None,
        required_group="MeridianNetworkUsers",
        groups_header="x-authenticated-groups",
        is_authorized=False,
        user_required=True,
        message=(
            "IAM Domain user integration is not yet enabled. "
            "Security actions require a manually entered user name."
        ),
    )
