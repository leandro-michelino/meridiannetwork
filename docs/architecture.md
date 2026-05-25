# Architecture

## Goal

Meridian centralises OCI network observability into a single operational dashboard: live inventory,
topology visualisation, route-issue detection, and security-posture analysis — all running from a
small OCI Compute VM inside the tenant it monitors.

---

## Runtime Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│  Browser                                                            │
│  frontend/dist/index.html (built single-page dashboard artifact)     │
│                                                                     │
│  • Region selector / async collection poll (3-15 s backoff)        │
│  • Per-region status panel: Ready / Collecting / Failed             │
│  • Topology canvas (Overview / Layers / VCN focus)                  │
│  • Security posture findings, route-issue analysis                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP (port 80)
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  Nginx                                                             │
│  /            → serve /var/www/meridian/index.html (no-cache)       │
│  /version.json → deployed frontend Git revision (no-cache)          │
│  /api/*        → proxy_pass http://127.0.0.1:8080                  │
│  /healthz      → proxy_pass http://127.0.0.1:8080                  │
│  /readyz       → proxy_pass http://127.0.0.1:8080                  │
│  /docs         → proxy_pass http://127.0.0.1:8080  (Swagger UI)    │
└────────────────────────────┬───────────────────────────────────────┘
                             │ loopback
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  FastAPI / uvicorn  (127.0.0.1:8080)                               │
│  systemd service: meridian-api                                     │
│  EnvironmentFile: /opt/meridian/config/meridian.env                │
│                                                                    │
│  Routers                                                           │
│  ├── health    GET /healthz  GET /readyz  GET /api/version         │
│  ├── scope     GET /api/regions/available                          │
│  │             GET /api/regions/active                             │
│  │             GET /api/compartments                               │
│  ├── preflight GET /api/preflight                                  │
│  ├── network   GET /api/dashboard?regions=&async_collect=true      │
│  │             GET /api/vcns                                       │
│  │             GET /api/subnets                                    │
│  │             GET /api/gateways                                   │
│  │             GET /api/route-tables                               │
│  │             GET /api/route-issues                               │
│  │             GET /api/security-lists                             │
│  │             GET /api/network-security-groups                    │
│  │             GET /api/topology                                   │
│  └── security  GET /api/security/posture                          │
│                                                                    │
│  Async collection pipeline                                         │
│  ├── ThreadPoolExecutor (4 workers, one job per region)            │
│  ├── In-memory snapshot cache  (MERIDIAN_INVENTORY_CACHE_TTL_SECONDS)│
│  └── On-disk snapshot cache   (MERIDIAN_INVENTORY_SNAPSHOT_DIR)    │
│       /opt/meridian/data/snapshots/snapshot_<region>_<hash>.json   │
└────────────────────────────┬───────────────────────────────────────┘
                             │ OCI SDK (oci-python-sdk)
                             │ Auth: instance_principal | config_file
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  OCI APIs                                                          │
│  ├── Identity  – compartment discovery (list_compartments)         │
│  ├── Core VCN  – VCNs, Subnets, IGW, NAT, SGW, DRG               │
│  │              Route Tables, Security Lists, NSGs                 │
│  └── Resource Search – optional scope narrowing (OCID-based)       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Topology (Terraform + Ansible)

```text
OCI Tenancy
└── Compartment: meridian_compartment_ocid
    ├── VCN  (10.0.0.0/24)
    │   ├── Public Subnet  (10.0.0.0/28)
    │   │   └── Security List  (ingress: admin_cidr_blocks → 22, 80, 443)
    │   └── Internet Gateway
    │
    ├── Compute Instance  (Oracle Linux, flex shape)
    │   ├── Nginx             → serves built dashboard + proxies /api
    │   ├── meridian-api      → FastAPI / uvicorn on 127.0.0.1:8080
    │   └── /opt/meridian/
    │       ├── backend/          (copied by Ansible)
    │       ├── config/meridian.env
    │       └── data/snapshots/   (persistent region snapshots)
    │
    └── IAM (optional, Terraform-managed)
        ├── Dynamic Group: meridian-dynamic-group
        │   match: instance.id = <instance_ocid>
        └── Policy: meridian-policy
            allow dynamic-group meridian-dynamic-group to read
              virtual-network-family, vcns, subnets, ...
              in tenancy
```

---

## Data Flow: Async Region Collection

```text
UI selects regions
      │
      │ GET /api/dashboard?regions=A,B&async_collect=true
      ▼
network.py: _async_dashboard_snapshot()
      │
      ├── for each region:
      │   ├── cache HIT (fresh)?  → return snapshot immediately
      │   ├── disk snapshot HIT?  → serve stale + launch refresh job
      │   └── no cache?           → launch collection job
      │
      │   ThreadPoolExecutor.submit(_collect)
      │         │
      │         ▼
      │   _build_dashboard_snapshot(regions=[region])
      │         │  OCI SDK calls (VCN, Subnet, GW, RT, SL, NSG)
      │         ▼
      │   snapshot { vcns, subnets, ..., collected_at, duration_seconds }
      │         │
      │         ├── write → _dashboard_snapshots (in-memory)
      │         └── write → data/snapshots/snapshot_<region>_<hash>.json
      │
      └── aggregate partial snapshots → return response
            collection.regions[]: id, status, resource_counts,
                                   last_updated, duration_seconds, error

UI receives response:
  status=collecting → poll again after 3 s (backs off to 15 s)
  status=ready      → render inventory + topology
```

---

## Security Boundary

- Meridian runs with read-only OCI permissions (network observability only).
- The Compute instance authenticates via Instance Principal — no API keys on disk.
- Nginx restricts SSH and web ingress to `admin_cidr_blocks` via the OCI Security List.
- The API binds only to loopback (`127.0.0.1`); external access is exclusively through Nginx.
- The env file (`meridian.env`) is mode `0640`, owned by the `meridian` system user.
- No write actions to OCI resources are implemented.

---

## Planned Extensions

- IAM domain user authentication (header-based, already stubbed in Settings).
- OCI Object Storage archival for security action audit log.
- Scheduled background refresh (APScheduler or systemd timer) for tenant-wide pre-warm.
- Compartment-tag-based scope filtering (delta refresh for large tenants with 400+ compartments).
