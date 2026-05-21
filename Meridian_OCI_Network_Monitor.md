# Meridian - OCI Network Monitor

Unified OCI Network Observability Dashboard

Version: 1.2
Status: In Design
Owner: Leandro
Last updated: 2026-05-21

## 1. Overview

Meridian is a self-hosted dashboard for consolidated Oracle Cloud Infrastructure network observability. It is designed for cloud operators, solution engineers, and network teams that need a single operational view across OCI regions, compartments, and network services.

## 2. Problem Statement

OCI network visibility is powerful but fragmented across several consoles and services:

- Network Command Center.
- Network Visualizer.
- Path Analyzer.
- Metrics Explorer.
- Logging and Logging Analytics.
- OCI Console resource pages for VCNs, DRGs, VPNs, FastConnect, Load Balancers, and DNS.
- Alarms and Notifications.
- Audit events.

An operator often has to move through several screens to answer simple operational questions:

- Which VCNs and gateways are unhealthy?
- Which instance is generating the most network traffic?
- Which security rule is exposing an environment?
- Which DRG route changed?
- Which Load Balancer backend is degraded?
- Which certificate is close to expiry?
- Which compartment or region is driving network cost?

## 3. Solution

Meridian aggregates OCI network inventory, metrics, logs, alarms, audit events, and topology context into a unified dashboard.

The intended deployment model is self-hosted inside the customer tenancy, using instance principal authentication for production and OCI API key authentication for development.

## 4. Primary Use Cases

- Daily network operations.
- NOC dashboard view.
- Customer demos and pre-sales walkthroughs.
- Disaster recovery readiness validation.
- Network troubleshooting.
- Security exposure reviews.
- Load balancer and certificate health checks.
- Egress cost visibility.
- Executive reporting with OCI Generative AI assistance.

## 5. High-Level Architecture

```text
OCI Tenancy
  |
  +-- Monitoring
  +-- Logging and Logging Analytics
  +-- Audit
  +-- Networking APIs
  +-- Load Balancer APIs
  +-- DNS APIs
  +-- Generative AI APIs
  |
  +-- Meridian Backend
        |
        +-- Python FastAPI
        +-- OCI SDK clients
        +-- Scheduler
        +-- Optional Redis cache
        |
        +-- Meridian Frontend
              |
              +-- React dashboard
              +-- Charts
              +-- Topology views
              +-- Reports
```

## 6. Current Repository Baseline

This repository currently provides the deployment foundation:

- Terraform baseline for OCI network and compute resources.
- Ansible bootstrap for the Meridian host.
- Static dashboard prototype.
- Documentation and manual validation guidance.

The application backend and production frontend are planned work and are not implemented yet.

## 7. Current Infrastructure Baseline

Terraform creates:

- VCN.
- Public subnet.
- Internet gateway.
- Route table.
- Security list constrained by `admin_cidr_blocks`.
- Compute instance using Oracle Linux.
- Optional dynamic group.
- Optional IAM policy for instance principal access.

Ansible configures:

- Base OS packages.
- Nginx.
- Podman-ready runtime packages.
- Firewalld.
- Meridian runtime directories.
- Static dashboard publication.

## 8. Technical Stack

### Backend

Planned:

- Python.
- FastAPI.
- OCI Python SDK.
- Pydantic.
- APScheduler or Celery.
- httpx.
- Redis as optional cache.
- pytest.

### Frontend

Planned:

- React.
- TypeScript.
- Recharts.
- React Flow or a comparable topology library.
- TanStack Table.
- Browser local storage for lightweight user preferences.

### Infrastructure

Current:

- Terraform.
- Ansible.
- OCI Compute.
- Oracle Linux.
- Nginx.
- Podman-ready host packages.

Future:

- Containerized backend and frontend.
- HTTPS.
- Private access pattern.
- Remote Terraform state.
- Optional OKE deployment pattern.

## 9. Authentication Model

### Development

Use OCI API key authentication through a configured OCI CLI profile.

### Production

Use OCI instance principal authentication through:

- Dynamic group.
- Read-oriented IAM policy.
- Instance metadata service.

## 10. IAM Intent

Meridian should use the minimum permissions required for network observability.

Initial read-oriented permission areas:

- Compartments.
- Virtual network resources.
- Compute instance metadata.
- Monitoring metrics.
- Logging resources.
- Alarms.
- Audit events.
- Load Balancer resources.
- Network Load Balancer resources.
- Private DNS resources.
- DRG resources.
- FastConnect and IPSec resources.
- OCI Generative AI invocation where enabled.

Write permissions are intentionally out of scope for the initial product.

## 11. Dashboard Modules

### 11.1 VCN Overview

Shows VCNs by compartment and region.

Expected fields:

- VCN name.
- OCID.
- CIDR blocks.
- Region.
- Compartment.
- Lifecycle state.
- Subnet count.
- Associated gateways.
- Route table count.
- Security list and NSG summary.

### 11.2 Gateway Status Panel

Monitors:

- Internet Gateways.
- NAT Gateways.
- Service Gateways.
- Local Peering Gateways.
- Dynamic Routing Gateways.
- FastConnect virtual circuits.
- Site-to-Site VPN tunnels.

Expected metrics:

- Packets in and out.
- Bytes in and out.
- Drops.
- Errors.
- Status.
- Attachment state.
- Bandwidth utilization where available.

### 11.3 VCN Flow Logs Viewer

Provides flow log analysis for accepted and rejected traffic.

Expected capabilities:

- Filter by region.
- Filter by compartment.
- Filter by VCN and subnet.
- Filter by source IP and destination IP.
- Filter by protocol and port.
- Filter by action.
- Show top source IPs.
- Show top destination IPs.
- Show rejected traffic trends.
- Export filtered results.

### 11.4 Network Alarms Center

Aggregates active network-related alarms.

Expected fields:

- Alarm name.
- Severity.
- Resource.
- Region.
- Compartment.
- Trigger time.
- Duration.
- Metric query.
- Link to OCI Console.

### 11.5 Inter-Region Latency

Shows latency between configured OCI regions.

Expected capabilities:

- Region pair matrix.
- 24-hour and 7-day history.
- Threshold alerts.
- DR readiness correlation.
- Visual indication for degraded pairs.

### 11.6 VNIC and Compute Top Consumers

Ranks instances by network usage.

Expected metrics:

- `VnicFromNetworkBytes`.
- `VnicToNetworkBytes`.
- `VnicFromNetworkPackets`.
- `VnicToNetworkPackets`.
- `VnicIngressDrops`.
- `VnicEgressDrops`.

Expected views:

- Top consumers by total bytes.
- Top egress sources.
- Drop rate.
- Shape.
- Region.
- Compartment.
- VCN.
- Multi-VNIC drill-down.
- Direct OCI Console link.

### 11.7 Disaster Recovery Readiness

Summarizes whether the network is ready for failover.

Expected checks:

- Gateway status.
- VPN and FastConnect status.
- DRG route presence.
- Route symmetry between primary and standby regions.
- Synthetic checks.
- Inter-region latency.
- Blocking risks.

### 11.8 Region Selector

Expected behavior:

- Home region is fixed and cannot be removed.
- Additional regions can be added and removed.
- Regions are persisted locally.
- API calls are made in parallel per selected region.
- Dashboard KPIs aggregate across selected regions.

Initial supported OCI regions:

- `eu-frankfurt-1`
- `eu-amsterdam-1`
- `eu-london-1`
- `eu-paris-1`
- `eu-milan-1`
- `eu-stockholm-1`
- `eu-madrid-1`
- `us-ashburn-1`
- `us-phoenix-1`
- `us-chicago-1`
- `ca-toronto-1`
- `af-johannesburg-1`
- `me-dubai-1`
- `me-jeddah-1`
- `ap-tokyo-1`
- `ap-singapore-1`
- `ap-sydney-1`
- `ap-mumbai-1`
- `sa-saopaulo-1`
- `sa-vinhedo-1`

### 11.9 Compartment Switcher

Expected behavior:

- Hierarchical compartment tree.
- Multi-select.
- Select all.
- Clear selection.
- Local persistence.
- Active compartment count in the top bar.
- All dashboard panels filter by selected compartments.

### 11.10 Security Posture Panel

Analyzes exposure without depending on OCI Cloud Guard.

Risk indicators:

- SSH open to `0.0.0.0/0`.
- RDP open to `0.0.0.0/0`.
- All protocols open to `0.0.0.0/0`.
- Large source CIDR ranges.
- Public subnets with broad ingress.
- NSG or security list rules with missing ownership tags.

Expected outputs:

- Risk score by VCN.
- Risk score by compartment.
- Risk score by region.
- List of risky rules.
- Direct OCI Console links.
- Audit history for changes.

### 11.11 OKE Network Health

Monitors network-related OKE health.

Expected checks:

- Cluster endpoint mode.
- Node pool subnet IP capacity.
- VCN-native CNI status.
- LoadBalancer services.
- Ingress controllers.
- Node VNIC bandwidth.
- API server reachability.

### 11.12 Cost-Aware Egress

Correlates egress traffic with cost estimates.

Expected outputs:

- Egress by Internet Gateway.
- Egress by NAT Gateway.
- Egress by instance.
- Top egress consumers.
- Monthly projection.
- Region comparison.
- Threshold alerts.

### 11.13 Change Feed

Uses OCI Audit events to show recent network changes.

Tracked events:

- VCN creation and deletion.
- Subnet changes.
- Gateway changes.
- Security List changes.
- NSG changes.
- Route Table changes.
- DRG attachment changes.
- VPN and FastConnect changes.
- Load Balancer listener and backend changes.
- DNS zone and resolver changes.

### 11.14 Synthetic Health Checks

Runs active connectivity checks.

Expected check types:

- ICMP ping where permitted.
- TCP connect.
- HTTP health probe.
- DNS lookup.

Expected outputs:

- Latency.
- Packet loss.
- Uptime percentage.
- Failure count.
- Region and compartment context.
- History by target.

### 11.15 NOC Mode

Full-screen operations view.

Expected behavior:

- Reduced navigation.
- High contrast.
- Larger operational typography.
- Auto-refresh.
- Last refresh timestamp.
- Active alarms.
- Gateway status.
- Inter-region latency.
- Rotation across selected regions.

### 11.16 Export and Notifications

Expected exports:

- PDF snapshot.
- CSV metrics.
- CSV flow logs.
- Security posture PDF.

Expected notification channels:

- OCI Notifications.
- Slack webhook.
- Microsoft Teams webhook.
- OCI Email Delivery.

### 11.17 Load Balancer Health

Covers OCI Load Balancer and Network Load Balancer.

Expected checks:

- Backend set health.
- Individual backend health.
- Listener status.
- Routing policies.
- Request rate.
- Error rate.
- Active connections.
- Bytes processed.
- Response time.
- Certificate expiry.

### 11.18 Private DNS Visibility

Shows private DNS configuration and DNS-related risks.

Expected resources:

- Private zones.
- Resolvers.
- Resolver endpoints.
- Resolver rules.
- Views.
- Records.

Expected issues:

- Zone without records.
- Zone without expected VCN association.
- Resolver without forwarding rules where expected.
- Peered VCNs without DNS forwarding.
- Records pointing outside expected CIDRs.
- Very low TTL records.
- NXDOMAIN patterns.

### 11.19 DRG Route Inspector

Provides deep visibility into DRG routing.

Expected views:

- DRGs by region.
- Attachments by type.
- Route tables.
- Route rules.
- Static routes.
- BGP routes.
- Import and export policies.
- Overlapping prefixes.
- Orphan routes.
- Route table comparison for DR.

### 11.20 OCI Generative AI Intelligence Layer

Optional AI assistance using OCI Generative AI.

Principles:

- No vector database required for the initial design.
- No RAG infrastructure required for the initial design.
- The dashboard sends already-collected context in the prompt.
- AI features are additive and can be disabled globally.
- Core dashboard features must work without AI.

Expected AI capabilities:

- Alarm explanation.
- Natural language flow log query assistance.
- Security posture executive narrative.
- Audit change impact analysis.
- DR readiness summary.

## 12. Planned API Families

### Scope and Inventory

```text
GET /api/regions/available
GET /api/regions/active
GET /api/compartments
GET /api/vcns
GET /api/subnets
GET /api/gateways
```

### Metrics and Alarms

```text
GET /api/gateways/metrics
GET /api/alarms/active
GET /api/latency/interregion
GET /api/vnics/top-consumers
GET /api/vnics/instance/{instance_id}/metrics
GET /api/vnics/anomalies
```

### Logs and Audit

```text
GET /api/flow-logs
GET /api/flow-logs/top-talkers
GET /api/audit/network-changes
```

### Security

```text
GET /api/security/posture
GET /api/security/risky-rules
GET /api/security/report
```

### Advanced Network Modules

```text
GET /api/oke/clusters
GET /api/oke/network-health
GET /api/cost/egress
GET /api/healthchecks
POST /api/healthchecks
GET /api/lb/list
GET /api/lb/{load_balancer_id}/backends
GET /api/lb/{load_balancer_id}/metrics
GET /api/lb/certificates
GET /api/dns/zones
GET /api/dns/resolvers
GET /api/dns/views
GET /api/dns/issues
GET /api/drg/list
GET /api/drg/{drg_id}/routes
GET /api/drg/{drg_id}/bgp
GET /api/drg/{drg_id}/policies
GET /api/drg/validation
```

### AI

```text
POST /api/genai/alarm/explain
POST /api/genai/flowlogs/query
POST /api/genai/security/narrative
POST /api/genai/audit/impact
POST /api/genai/dr/readiness-summary
```

## 13. Planned Data Sources

OCI service areas:

- Monitoring.
- Logging.
- Logging Analytics.
- Audit.
- Core Networking.
- Compute.
- Load Balancer.
- Network Load Balancer.
- DNS.
- DRG.
- FastConnect.
- Site-to-Site VPN.
- OKE.
- Price List.
- Notifications.
- Email Delivery.
- Generative AI.

## 14. Development Phases

### Phase 0 - Foundation

Status: in progress.

- Repository setup.
- Terraform OCI baseline.
- Ansible host bootstrap.
- Static dashboard prototype.
- Manual validation documentation.

### Phase 1 - Backend Base

- FastAPI skeleton.
- OCI SDK client factory.
- Authentication modes.
- Health endpoint.
- Structured logging.

### Phase 2 - Inventory Collection

- Regions.
- Compartments.
- VCNs.
- Subnets.
- Gateways.
- DRGs.
- Load Balancers.
- DNS resources.

### Phase 3 - Metrics

- OCI Monitoring queries.
- Gateway metrics.
- VNIC metrics.
- Top consumers.
- Alarms.

### Phase 4 - Logs and Audit

- Flow logs.
- Rejected traffic.
- Audit change feed.
- Change correlation.

### Phase 5 - Security and Governance

- Risk scoring.
- Risky rule detection.
- Security posture reports.
- Historical posture trend.

### Phase 6 - Advanced Modules

- OKE network health.
- Cost-aware egress.
- Synthetic health checks.
- Load Balancer health.
- Private DNS visibility.
- DRG route inspection.

### Phase 7 - Intelligence Layer

- Alarm explanations.
- Natural language flow log queries.
- Security narratives.
- Change impact summaries.
- DR readiness summaries.

### Phase 8 - Production Hardening

- HTTPS.
- Private access pattern.
- Remote Terraform state.
- Containerized deployment.
- Backup and recovery.
- Meridian self-monitoring.

## 15. Immediate Next Steps

1. Populate `terraform/terraform.tfvars`.
2. Run `make tf-init`.
3. Run `make tf-plan`.
4. Review IAM policy requirements.
5. Apply the OCI baseline in a test compartment.
6. Run `make deploy`.
7. Add the FastAPI backend skeleton.
8. Add the OCI SDK client factory.
9. Implement `GET /healthz`.
10. Implement compartments and regions endpoints.

