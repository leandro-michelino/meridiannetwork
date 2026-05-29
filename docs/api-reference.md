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
| GET    | `/api/version` | Deployment metadata — returns service version, Git revision, and build timestamp |

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
| GET    | `/api/dashboard/completeness` | Region coverage and collection completeness summary |

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
| GET    | `/api/security/finding-actions` | Implemented — list security finding workflow action history     |
| POST   | `/api/security/finding-actions` | Implemented — record a finding action                           |
| GET    | `/api/security/risky-rules` | Planned                                                            |
| GET    | `/api/security/report`     | Planned                                                             |

---

## Traffic

| Method | Path                            | Status                                                              |
| ------ | ------------------------------- | ------------------------------------------------------------------- |
| POST   | `/api/connectivity/check`       | Implemented — exact source/destination check through OCI Network Path Analyzer |
| GET    | `/api/traffic/telemetry/status` | Implemented — lightweight by default; VCN Flow Log coverage only with `check_vcns=true` |
| POST   | `/api/traffic/telemetry/enable` | Implemented — opt-in VCN Flow Log setup, gated by runtime config    |
| POST   | `/api/traffic/telemetry/disable` | Implemented — disables Meridian-created VCN Flow Logs for selected VCNs |
| GET    | `/api/traffic/flows`            | Implemented — searches recent VCN Flow Log records with VM/IP filters |

`POST /api/connectivity/check` accepts source and destination endpoints (`ip_address`, `compute_instance`, `vnic`, or
`subnet`), protocol (`TCP`, `UDP`, or `ICMP`), optional destination/source ports, region, compartment, and
`bidirectional`. It does not enable VCN Flow Logs.

Example request:

```json
{
  "source": {
    "type": "ip_address",
    "value": "10.42.10.142"
  },
  "destination": {
    "type": "ip_address",
    "value": "10.42.20.44"
  },
  "protocol": "TCP",
  "destination_port": 443,
  "region": "me-abudhabi-1",
  "compartment_id": "ocid1.compartment.oc1..example",
  "bidirectional": true
}
```

Useful response fields:

- `status`: `reachable`, `blocked`, `running`, `failed`, `disabled`, `missing_scope`, or `unknown`.
- `reachable`: boolean when OCI returns a final path answer; `null` while still running or when disabled.
- `cost_impact`: currently `no_flow_logs_enabled` for Connectivity Check responses.
- `findings`: the human-readable blockers or service-limit notes.
- `next_actions`: the short "try this next" list shown in the dashboard.
- `hops`: route/security actions from OCI Network Path Analyzer when a path result is available.

If `status` is `running`, the API has returned before the OCI work request finished. Run the same check again after a
moment. If `status` is `failed` and the message mentions the Network Path Analyzer compartment limit, the app has already
cleaned up the raw OCI error into a customer-friendly explanation.

`GET /api/traffic/flows` accepts `regions`, `compartment_ids`, `source_ip`, `destination_ip`, `port`, `action`,
`lookback_minutes`, and `limit`.

Traffic telemetry is intentionally separate from Connectivity Check:

- `GET /api/traffic/telemetry/status` is lightweight by default and does not scan all VCNs.
- Add `check_vcns=true` only when you want to verify VCN Flow Log coverage.
- `POST /api/traffic/telemetry/enable` is blocked unless `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true`. It accepts
  optional `enablement_minutes`, but the server clamps the lease to `max_enablement_minutes` (60 by default).
- `POST /api/traffic/telemetry/disable` removes Meridian-created Flow Logs for the selected VCNs.
- Status and enable responses can include `expires_at`, so the dashboard can show when automatic cleanup will run.

Example enable request:

```json
{
  "regions": ["me-abudhabi-1"],
  "compartment_ids": ["ocid1.compartment.oc1..example"],
  "vcn_ids": ["ocid1.vcn.oc1..example", "ocid1.vcn.oc1..example2"],
  "enablement_minutes": 30
}
```

Expired leases are cleaned up by the API process. Cleanup disables the Flow Log and deletes the Meridian-created log
resource when the OCI Logging client supports deletion. Previously ingested records remain subject to the customer's OCI
Logging retention policy.

---

## Identity

| Method | Path                    | Status                                      |
| ------ | ----------------------- | ------------------------------------------- |
| GET    | `/api/identity/context` | Implemented — runtime identity context used by the dashboard |

---

## Export

All export endpoints accept `regions`, `compartment_ids`, and where applicable `vcn_id`.

| Method | Path                                | Status                                      |
| ------ | ----------------------------------- | ------------------------------------------- |
| GET    | `/api/export/security-posture.csv`  | Implemented — CSV security findings export |
| GET    | `/api/export/inventory.csv`         | Implemented — CSV VCN, subnet, and gateway export |
| GET    | `/api/export/completeness.csv`      | Implemented — CSV region coverage export   |

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
/api/notifications/*
/api/genai/*
```
