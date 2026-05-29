# Architecture

## Goal

Meridian centralises OCI network observability into a single operational dashboard: live inventory,
topology visualisation, route-issue detection, and security-posture analysis. It runs from a small
OCI Compute VM inside the tenant it monitors.

## Runtime Architecture

```text
+-----------------------------------------------------------------------+
| Browser                                                               |
| frontend/dist/index.html                                              |
|                                                                       |
| - Region selector, selected-region coverage, and saved region views   |
| - Async collection polling with 3-15 second backoff                   |
| - Topology canvas with overview, layer, VCN focus, and quick filters  |
| - Security findings with workflow filter and OCI Console links        |
| - Deployment badge sourced from window.MERIDIAN_BUILD/version APIs    |
+----------------------------------+------------------------------------+
                                   |
                                   | HTTP port 80
                                   v
+-----------------------------------------------------------------------+
| Nginx                                                                 |
| /              -> /var/www/meridian/index.html with no-cache headers  |
| /version.json  -> deployed frontend Git revision with no-cache headers|
| /api/*         -> http://127.0.0.1:8080                               |
| /healthz       -> http://127.0.0.1:8080                               |
| /readyz        -> http://127.0.0.1:8080                               |
| /docs          -> http://127.0.0.1:8080 Swagger UI                   |
+----------------------------------+------------------------------------+
                                   |
                                   | loopback
                                   v
+-----------------------------------------------------------------------+
| FastAPI / uvicorn on 127.0.0.1:8080                                   |
| systemd service: meridian-api                                         |
| EnvironmentFile: /opt/meridian/config/meridian.env                    |
|                                                                       |
| Routers                                                               |
| - health:   GET /healthz, GET /readyz, GET /api/version               |
| - scope:    GET /api/regions/available, /active, /compartments        |
| - preflight GET /api/preflight                                        |
| - network:  GET /api/dashboard?regions=&async_collect=true            |
|             GET /api/vcns, /subnets, /gateways, /route-tables         |
|             GET /api/route-issues, /security-lists, /topology         |
|             GET /api/network-security-groups                          |
| - security: GET /api/security/posture                                 |
|                                                                       |
| Collection pipeline                                                   |
| - ThreadPoolExecutor: 4 workers, one collection job per region         |
| - In-memory cache: MERIDIAN_INVENTORY_CACHE_TTL_SECONDS               |
| - Disk cache: MERIDIAN_INVENTORY_SNAPSHOT_DIR                         |
|   /opt/meridian/data/snapshots/snapshot_<region>_<hash>.json          |
+----------------------------------+------------------------------------+
                                   |
                                   | OCI SDK, instance principal or config file
                                   v
+-----------------------------------------------------------------------+
| OCI APIs                                                              |
| - Identity: compartment discovery                                     |
| - Core VCN: VCNs, subnets, gateways, route tables, SLs, NSGs          |
| - Resource Search: optional OCID-based scope narrowing                |
+-----------------------------------------------------------------------+
```

## Frontend Build And Deploy Flow

```text
Developer workstation
  |
  | make frontend-build
  v
frontend/scripts/build.mjs
  |
  | reads source dashboard shell
  v
oci_network_monitor_dashboard_v2.html
  |
  | imports frontend/src/build-info.mjs
  | imports frontend/src/html-artifact.mjs
  v
frontend/dist/
  |-- index.html     built dashboard with injected build metadata
  `-- version.json   app, artifact, version, revision, built_at, dirty

make deploy
  |
  | renders inventory from Terraform outputs
  | runs ansible/playbooks/bootstrap.yml
  v
OCI VM
  |-- /var/www/meridian/index.html
  |-- /var/www/meridian/version.json
  |-- /opt/meridian/backend/
  `-- /opt/meridian/config/meridian.env
```

The same Git revision is exposed in the dashboard badge, `/version.json`, and `GET /api/version`.
After a clean deployment, both version endpoints should report `dirty: false`.

## Deployment Topology

```text
OCI Tenancy
`-- Compartment: meridian_compartment_ocid
    |-- VCN 10.0.0.0/24
    |   |-- Public Subnet 10.0.0.0/28
    |   |   `-- Security List
    |   |       `-- ingress from admin_cidr_blocks to 22, 80, 443
    |   |-- Internet Gateway
    |   `-- Optional NAT Gateway for restricted outbound TCP 443
    |
    |-- Compute Instance, Oracle Linux flex shape
    |   |-- Nginx
    |   |   |-- serves built dashboard and version.json
    |   |   `-- proxies /api, /healthz, /readyz, /docs
    |   |-- meridian-api
    |   |   `-- FastAPI / uvicorn on 127.0.0.1:8080
    |   `-- /opt/meridian/
    |       |-- backend/
    |       |-- config/meridian.env
    |       `-- data/snapshots/
    |
    `-- IAM, optional Terraform-managed resources
        |-- Dynamic Group: meridian-dynamic-group
        |   `-- match rule for the Meridian Compute instance
        `-- Policy: meridian-policy
            `-- read access for compartments and Virtual Networking

Optional Object Storage
`-- Bucket: <project>-<environment>-action-history
    `-- Prefix: <project>/security-actions/
```

## Selected-Region Data Flow

```text
User selects one or more regions
  |
  | dashboard stores current scope and optional saved views in localStorage
  v
UI request
  |
  | GET /api/dashboard?regions=A,B&async_collect=true
  v
backend/app/routers/network.py
  |
  | _async_dashboard_snapshot()
  v
For each requested region
  |
  |-- fresh memory cache hit -> return snapshot immediately
  |-- disk snapshot hit      -> return stale snapshot and refresh in background
  `-- no cache               -> submit collection job
                              |
                              v
                         _build_dashboard_snapshot(regions=[region])
                              |
                              | OCI SDK calls for VCN, subnet, gateway,
                              | route table, security list, and NSG data
                              v
                         snapshot payload
                              |
                              |-- write in-memory cache
                              `-- write disk snapshot

Backend response
  |
  | collection.status = collecting -> UI polls again with backoff
  | collection.status = ready      -> UI renders scoped coverage, tables, topology, findings
  v
Exports and coverage panels use the selected region scope by default
```

## Security Boundary

- Meridian runs with read-only OCI permissions for network observability.
- The Compute instance authenticates with instance principal in production; no API keys are required on the VM.
- Nginx ingress is controlled by `admin_cidr_blocks` in the OCI Security List.
- Optional NAT egress can restrict default outbound traffic while preserving scoped public ingress.
- The API binds only to `127.0.0.1`; external access is through Nginx.
- `/opt/meridian/config/meridian.env` is owned by the `meridian` system user and is not committed.
- Terraform state, generated inventory, and frontend build output are ignored by Git.
- OCI resource mutation is limited to the explicitly gated Traffic Telemetry enablement flow, which can create VCN Flow
  Log resources only when `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true` and the runtime principal has matching
  permissions.

## Planned Extensions

- IAM domain user authentication.
- OCI Object Storage archival for security action audit history.
- Scheduled background refresh for tenant-wide cache pre-warming.
- Compartment tag based scope filtering for large tenancies.
