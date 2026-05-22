# API Reference

All endpoints are served by the Meridian FastAPI backend and proxied through Nginx.
Base URL: `http://<host>/`

## Conventions

- All endpoints return JSON.
- Filter parameters accept comma-separated values: `regions=eu-frankfurt-1,me-abudhabi-1`.
- Error responses use a consistent envelope:

```json
{
  "detail": {
    "code": "OCI_CLIENT_ERROR",
    "message": "Human-readable description"
  }
}
```

- When `MERIDIAN_ENABLE_LIVE_OCI=false` (default), inventory endpoints return empty lists without
  hitting OCI APIs. Health and preflight endpoints always respond.

---

## Health

| Method | Path      | Description                                                         |
| ------ | --------- | ------------------------------------------------------------------- |
| GET    | `/healthz` | Liveness — returns service name, version, environment, status      |
| GET    | `/readyz`  | Readiness — indicates whether the API is ready to serve live OCI calls |

`/readyz` returns `status: degraded` when live OCI mode is enabled but `MERIDIAN_TENANCY_OCID` is
not configured.

---

## Preflight

| Method | Path             | Description                                                      |
| ------ | ---------------- | ---------------------------------------------------------------- |
| GET    | `/api/preflight` | Runtime readiness checks for OCI connectivity and permissions    |

Runs checks for: auth mode, tenancy configuration, compartment discovery, and required network
inventory reads (VCN list, security list, NSG list). Each check returns `name`, `status`
(`pass` / `fail` / `skip`), `message`, and `action`.

---

## Scope

| Method | Path                       | Description                                                              |
| ------ | -------------------------- | ------------------------------------------------------------------------ |
| GET    | `/api/regions/available`   | All known OCI regions with geo and home-region flag                      |
| GET    | `/api/regions/active`      | Regions configured via `MERIDIAN_HOME_REGION` + `MERIDIAN_ACTIVE_REGIONS` |
| GET    | `/api/compartments`        | Accessible compartments discovered from the tenancy root                 |

---

## Dashboard (aggregate)

| Method | Path             | Description                                            |
| ------ | ---------------- | ------------------------------------------------------ |
| GET    | `/api/dashboard` | Full inventory snapshot — all resource types in one response |

Query parameters:

| Parameter         | Type   | Description                                                              |
| ----------------- | ------ | ------------------------------------------------------------------------ |
| `regions`         | string | Comma-separated region IDs                                               |
| `compartment_ids` | string | Comma-separated compartment OCIDs                                        |
| `vcn_id`          | string | Optional VCN OCID filter                                                 |
| `async_collect`   | bool   | `true` = return immediately with cached data, collect in background      |

When `async_collect=true` the response includes a `collection` object:

```json
{
  "collection": {
    "status": "collecting | ready | ready_with_warnings | failed",
    "requested_regions": ["me-abudhabi-1"],
    "completed_regions": [],
    "pending_regions": ["me-abudhabi-1"],
    "issues": [],
    "regions": [
      {
        "id": "me-abudhabi-1",
        "status": "collecting",
        "resource_counts": {},
        "last_updated": null,
        "duration_seconds": null,
        "error": null
      }
    ]
  }
}
```

The UI polls every 3–15 s (exponential backoff) until `status` is no longer `collecting`.
Completed snapshots are written to `MERIDIAN_INVENTORY_SNAPSHOT_DIR` and reused across restarts.

---

## Network Inventory

All endpoints accept `regions` and `compartment_ids` query parameters.
`subnets`, `gateways`, `route-tables`, `security-lists`, `network-security-groups`, and `topology`
also accept `vcn_id`.

| Method | Path                              | Status                                        |
| ------ | --------------------------------- | --------------------------------------------- |
| GET    | `/api/vcns`                       | Implemented                                   |
| GET    | `/api/subnets`                    | Implemented                                   |
| GET    | `/api/gateways`                   | Implemented — IGW, NAT, SGW, DRG              |
| GET    | `/api/route-tables`               | Implemented                                   |
| GET    | `/api/route-issues`               | Implemented — route table analysis            |
| GET    | `/api/security-lists`             | Implemented                                   |
| GET    | `/api/network-security-groups`    | Implemented — with ingress/egress rule summaries |
| GET    | `/api/topology`                   | Implemented — graph derived from all inventory types |
| GET    | `/api/drgs`                       | Planned                                       |
| GET    | `/api/vpns`                       | Planned                                       |
| GET    | `/api/fastconnect`                | Planned                                       |

---

## Security

| Method | Path                       | Status                                                              |
| ------ | -------------------------- | ------------------------------------------------------------------- |
| GET    | `/api/security/posture`    | Implemented — broad ingress/egress risk checks across SLs and NSGs |
| GET    | `/api/security/risky-rules` | Planned                                                            |
| GET    | `/api/security/report`     | Planned                                                             |

---

## Planned Endpoint Families

The following endpoint families are specified but not yet implemented:

```text
/api/gateways/metrics
/api/flow-logs
/api/audit/network-changes
/api/lb/*
/api/dns/*
/api/drg/*
/api/oke/*
/api/cost/*
/api/healthchecks
/api/export/*
/api/notifications/*
/api/genai/*
```
