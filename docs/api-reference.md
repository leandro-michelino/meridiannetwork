# API Reference

This document describes the Meridian API surface. Some endpoints are implemented in the current FastAPI foundation; the remaining endpoint families are the working contract for future development.

## Conventions

- All endpoints return JSON.
- All list endpoints support pagination once backed by live OCI calls.
- All OCI resource responses should include `id`, `name`, `region`, `compartment_id`, `lifecycle_state`, and `time_created` where available.
- Error responses should use a consistent structure:

```json
{
  "error": {
    "code": "OCI_REQUEST_FAILED",
    "message": "Human-readable error",
    "request_id": "optional-provider-request-id"
  }
}
```

## Health

```text
GET /healthz
GET /readyz
GET /api/preflight
```

Status: implemented.

`GET /api/preflight` returns runtime readiness checks for live OCI mode, auth mode, tenancy configuration, monitored
compartments, configured regions, OCI SDK signer creation, compartment discovery permission, and required network
inventory reads.

## Scope

```text
GET /api/regions/available
GET /api/regions/active
GET /api/compartments
```

Status: implemented.

## Network Inventory

```text
GET /api/vcns
GET /api/subnets
GET /api/gateways
GET /api/route-tables
GET /api/route-issues
GET /api/security-lists
GET /api/network-security-groups
GET /api/topology
GET /api/drgs
GET /api/vpns
GET /api/fastconnect
```

Status:

- `GET /api/vcns`: implemented.
- `GET /api/subnets`: implemented.
- `GET /api/gateways`: implemented for Internet Gateways, NAT Gateways, Service Gateways, and DRGs.
- `GET /api/route-tables`: implemented.
- `GET /api/route-issues`: implemented for route table analysis.
- `GET /api/security-lists`: implemented.
- `GET /api/network-security-groups`: implemented with ingress and egress rule summaries.
- `GET /api/topology`: implemented as a graph derived from VCNs, subnets, gateways, route tables, security lists, and NSGs.
- Remaining endpoints: planned.

Implemented query parameters:

```text
GET /api/vcns?regions=eu-frankfurt-1,eu-madrid-1&compartment_ids=<ocid>,<ocid>
GET /api/subnets?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/gateways?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/route-tables?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/route-issues?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/security-lists?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/network-security-groups?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
GET /api/topology?regions=eu-frankfurt-1&compartment_ids=<ocid>&vcn_id=<vcn_ocid>
```

If live OCI mode is disabled, these endpoints return empty lists.

## Metrics

```text
GET /api/gateways/metrics
GET /api/vnics/top-consumers
GET /api/vnics/instance/{instance_id}/metrics
GET /api/vnics/anomalies
GET /api/latency/interregion
```

## Logs and Audit

```text
GET /api/flow-logs
GET /api/flow-logs/top-talkers
GET /api/audit/network-changes
```

## Security

```text
GET /api/security/posture
GET /api/security/risky-rules
GET /api/security/report
```

Status:

- `GET /api/security/posture`: implemented for initial broad ingress checks.
- Remaining endpoints: planned.

## Load Balancers

```text
GET /api/lb/list
GET /api/lb/{load_balancer_id}/backends
GET /api/lb/{load_balancer_id}/metrics
GET /api/lb/certificates
GET /api/lb/alerts
```

## DNS

```text
GET /api/dns/zones
GET /api/dns/resolvers
GET /api/dns/views
GET /api/dns/issues
GET /api/dns/query-stats
```

## DRG

```text
GET /api/drg/list
GET /api/drg/{drg_id}/routes
GET /api/drg/{drg_id}/bgp
GET /api/drg/{drg_id}/policies
GET /api/drg/validation
GET /api/drg/issues
```

## OKE

```text
GET /api/oke/clusters
GET /api/oke/network-health
```

## Cost

```text
GET /api/cost/egress
GET /api/cost/top-consumers
```

## Synthetic Checks

```text
GET /api/healthchecks
POST /api/healthchecks
GET /api/healthchecks/{healthcheck_id}/history
```

## Export

```text
GET /api/export/pdf
GET /api/export/csv
```

## Notifications

```text
GET /api/notifications/config
POST /api/notifications/webhook
```

## AI

```text
POST /api/genai/alarm/explain
POST /api/genai/flowlogs/query
POST /api/genai/security/narrative
POST /api/genai/audit/impact
POST /api/genai/dr/readiness-summary
```
