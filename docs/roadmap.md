# Roadmap

## Phase 0 - Repository and Deployment Foundation

Status: in progress.

- Terraform OCI baseline.
- Ansible host bootstrap.
- Static dashboard publishing.
- Documentation and manual validation.

## Phase 1 - Backend Foundation

Status: started.

- Python FastAPI application.
- OCI SDK client factory.
- Instance principal support.
- API key profile support for development.
- Health endpoint.
- Structured logging.

Implemented so far:

- FastAPI application factory.
- Health and readiness endpoints.
- Region scope endpoints.
- Compartment endpoint with optional live OCI mode.
- VCN and subnet inventory endpoints with optional live OCI mode.
- Gateway inventory endpoint with optional live OCI mode.
- Route table and security list inventory endpoints with optional live OCI mode.
- Network Security Group inventory endpoint with optional live OCI mode.
- Topology graph endpoint derived from live OCI inventory.
- OCI preflight endpoint for runtime IAM and network read validation.
- Initial security posture endpoint for public SSH, public RDP, and public all-protocol ingress in Security Lists and NSGs.
- OCI client factory.
- Backend tests.

## Phase 2 - Core Network Inventory

- Regions and compartments.
- VCNs, subnets, route tables, gateways, Security Lists, and NSGs.
- DRG attachments.
- VPN and FastConnect status.
- Normalized resource model.

## Phase 3 - Metrics and Alarms

- OCI Monitoring queries.
- Gateway metrics.
- VNIC top consumers.
- Active alarm aggregation.
- Threshold configuration.

## Phase 4 - Logs and Security Posture

- VCN Flow Logs.
- Rejected traffic analysis.
- Risky security list and NSG rules.
- Audit change feed.

## Phase 5 - Advanced Network Modules

- OKE network health.
- Load Balancer health and certificate expiry.
- Private DNS visibility.
- DRG route inspector.
- Synthetic health checks.
- Cost-aware egress.

## Phase 6 - Intelligence Layer

- Alarm explanation with OCI GenAI.
- Natural language flow log query assistance.
- Security risk narrative.
- Change impact analysis.
- DR readiness summary.

## Phase 7 - Production Hardening

- Remote Terraform state.
- HTTPS and private access pattern.
- Containerized backend/frontend.
- Keep the small OCI Compute VM as the first deployment target.
- Evaluate OCI Container Instances only after containerization.
- Evaluate OCI Functions only for asynchronous collectors and notifications.
- Manual release/deployment procedure unless automation is explicitly approved later.
- Automated tests.
- Observability for Meridian itself.
