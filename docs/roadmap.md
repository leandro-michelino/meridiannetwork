# Roadmap

## Phase 0 - Repository and Deployment Foundation

Status: **complete**.

- Terraform OCI baseline.
- Ansible host bootstrap.
- Static dashboard publishing.
- Documentation and manual validation.

## Phase 1 - Backend Foundation

Status: **complete**.

- Python FastAPI application with uvicorn and Nginx proxy.
- OCI SDK client factory.
- Instance principal and API key profile auth modes.
- Health and readiness endpoints.
- OCI preflight endpoint.
- Structured logging via systemd journal.

## Phase 2 - Core Network Inventory

Status: **complete**.

- Regions and compartments.
- VCNs, subnets, route tables, security lists, NSGs.
- Gateways: IGW, NAT, SGW, DRG.
- Route issue analysis: blackhole, duplicate defaults, invalid targets.
- Security posture: risky ingress/egress rule detection.
- Topology graph derived from live inventory.
- Async per-region collection with in-memory and on-disk snapshot cache.
- Per-region collection status UI panel with backoff polling.
- Buildable frontend artifact with browser E2E coverage.
- Saved region views, selected-region coverage, topology quick filters, and security workflow filtering.
- 45 backend tests and 5 dashboard browser E2E tests.

## Phase 3 - Metrics and Alarms

- OCI Monitoring queries.
- Gateway metrics (bytes, packets, drops, errors).
- VNIC top consumers.
- Active alarm aggregation.
- Inter-region latency matrix.

## Phase 4 - Logs and Audit

- VCN Flow Logs viewer.
- Rejected traffic analysis.
- Audit change feed for network resources.
- Change correlation across regions.

## Phase 5 - Advanced Network Modules

- DRG route inspector (route tables, BGP routes, import/export policies).
- OKE network health.
- Load Balancer health and certificate expiry.
- Private DNS visibility.
- Synthetic health checks.
- Cost-aware egress analysis.

## Phase 6 - Security and Governance

- Exportable security posture reports (PDF, CSV).
- Risky rule detail endpoint.
- OCI Notifications integration.
- Slack and Teams webhook targets.

## Phase 7 - Intelligence Layer

- Alarm explanation with OCI GenAI.
- Natural language flow log query assistance.
- Security risk narrative.
- Change impact analysis.
- DR readiness summary.

## Phase 8 - Production Hardening

- HTTPS with OCI Certificate.
- Private access pattern (no public IP).
- Remote Terraform state (OCI Object Storage backend).
- Containerized backend deployment.
- Meridian self-monitoring and alerting.
