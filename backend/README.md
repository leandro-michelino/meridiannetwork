# Meridian Backend

FastAPI backend foundation for Meridian.

## Current Scope

- Application factory.
- Health, readiness, and deployment version endpoints.
- OCI preflight endpoint for IAM and service readiness validation.
- OCI client factory abstraction.
- Regions endpoint.
- Compartments endpoint with live OCI support when enabled.
- VCN inventory endpoint with live OCI support when enabled.
- Subnet inventory endpoint with live OCI support when enabled.
- Gateway inventory endpoint with live OCI support when enabled.
- Route table, security list, and Network Security Group endpoints with live OCI support when enabled.
- Route issue endpoint for empty route tables, duplicate destinations, unresolved targets, disabled targets, and public default routes.
- Topology graph endpoint derived from live OCI network inventory when enabled.
- Initial security posture endpoint for broad Security List and NSG ingress exposure.
- Security finding action history endpoints.
- CSV export endpoints for inventory, coverage completeness, and security posture.
- Test suite for the implemented API surface.

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
```

## Run Locally

```bash
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8080
```

## Test

```bash
make backend-test
```

## OCI Modes

By default, live OCI calls are disabled so local development and tests work without credentials.

Enable live OCI calls with:

```bash
export MERIDIAN_ENABLE_LIVE_OCI=true
export MERIDIAN_OCI_AUTH=config_file
export MERIDIAN_OCI_PROFILE=DEFAULT
export MERIDIAN_TENANCY_OCID=ocid1.tenancy.oc1..example
export MERIDIAN_COMPARTMENT_IDS=ocid1.compartment.oc1..example
```

For production on an OCI Compute instance, use:

```bash
export MERIDIAN_ENABLE_LIVE_OCI=true
export MERIDIAN_OCI_AUTH=instance_principal
export MERIDIAN_TENANCY_OCID=ocid1.tenancy.oc1..example
export MERIDIAN_COMPARTMENT_IDS=ocid1.compartment.oc1..example
```

## Preflight

```bash
curl http://127.0.0.1:8080/api/preflight
```

The response reports live mode, auth mode, home region, active regions, monitored compartments, and pass/fail checks for
the OCI SDK signer, compartment discovery, and Virtual Networking read calls used by the dashboard.
