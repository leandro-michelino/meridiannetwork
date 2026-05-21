# Meridian Backend

FastAPI backend foundation for Meridian.

## Current Scope

- Application factory.
- Health and readiness endpoints.
- OCI client factory abstraction.
- Regions endpoint.
- Compartments endpoint with live OCI support when enabled.
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
PYTHONPATH=backend pytest backend/tests
```

## OCI Modes

By default, live OCI calls are disabled so local development and tests work without credentials.

Enable live OCI calls with:

```bash
export MERIDIAN_ENABLE_LIVE_OCI=true
export MERIDIAN_OCI_AUTH=config_file
export MERIDIAN_OCI_PROFILE=DEFAULT
export MERIDIAN_TENANCY_OCID=ocid1.tenancy.oc1..example
```

For production on an OCI Compute instance, use:

```bash
export MERIDIAN_ENABLE_LIVE_OCI=true
export MERIDIAN_OCI_AUTH=instance_principal
```

