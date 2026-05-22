# Project Status

Date: 2026-05-22

## Current Stage

Backend operational with full network inventory, async regional collection, topology, route analysis,
and security posture. Single-file dashboard deployed via Ansible to an OCI Compute VM.

## Implemented

### Infrastructure

- Terraform baseline: VCN, subnet, internet gateway, compute instance, IAM dynamic group and policy.
- Ansible bootstrap: Nginx, systemd service, environment configuration, persistent snapshot directory.
- Instance principal authentication for production; OCI config-file profile for development.

### Backend

- FastAPI with uvicorn on `127.0.0.1:8080`, proxied through Nginx on port 80.
- Health and readiness endpoints (`/healthz`, `/readyz`).
- OCI runtime preflight checks (`/api/preflight`).
- Region scope endpoints: available regions (all known OCI regions), active regions (configured subset).
- Compartment discovery from tenancy root.
- Full network inventory: VCNs, subnets, gateways (IGW, NAT, SGW, DRG), route tables, security lists, NSGs.
- Route issue analysis: blackhole targets, duplicate default routes, invalid entity references.
- Topology graph derived from live inventory relationships.
- Security posture: risky ingress/egress rule detection across Security Lists and NSGs.
- Async per-region collection pipeline with `ThreadPoolExecutor`.
- In-memory snapshot cache with configurable TTL.
- Persistent on-disk snapshot cache (survives restarts).
- Per-region collection status: `collecting`, `ready`, `ready_with_warnings`, `no_resources`, `failed`.
- OCI client factory abstraction.
- 27 backend tests covering all routers and services.

### Dashboard

- Single-file dashboard (`oci_network_monitor_dashboard_v2.html`) — no build step.
- Per-region collection status panel with spinner, duration, resource counts, relative timestamps.
- Async polling with exponential backoff (3–15 s).
- Interactive topology graph: Overview, Layers, VCN focus modes.
- Security posture panel with risky rule listings.
- Route issue analysis panel.
- Inventory tables for VCNs, subnets, gateways, route tables, security lists, NSGs.
- Region selector and compartment filter.
- OCI preflight access validation in top bar.
- Demo fallback data when `MERIDIAN_ENABLE_LIVE_OCI=false`.

## Not Yet Implemented

See [docs/module-map.md](docs/module-map.md) for the full planned feature list.

Key planned areas:

- VCN Flow Logs viewer.
- OCI Audit change feed.
- Metrics: gateway metrics, VNIC top consumers, inter-region latency.
- Advanced modules: DRG route inspector, OKE network health, load balancer health, private DNS, FastConnect/VPN.
- Intelligence layer: GenAI alarm explanation, natural language flow log query.
- Operations: PDF/CSV export, OCI Notifications, Slack/Teams webhooks.
- Production hardening: HTTPS, remote Terraform state, containerized deployment.
