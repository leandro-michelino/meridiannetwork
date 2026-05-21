# Project Status

Date: 2026-05-21

## Current Stage

Backend foundation scaffold.

## Available Now

- Product specification document.
- Static dashboard prototype.
- API-aware static dashboard with demo fallback data.
- Static dashboard inventory table with compartment context, subnet access classification, real OCI resource ID display, and pinned home-region navigation.
- Static dashboard live mode refreshes in the background every 5 seconds.
- Static dashboard operational panels use expanders to keep large inventories compact.
- Static dashboard topology nodes are draggable and keyboard-navigable.
- Static dashboard includes an OCI preflight expander for runtime IAM and network read validation.
- FastAPI backend foundation.
- Health and readiness endpoints.
- OCI preflight endpoint.
- Regions endpoints.
- Compartments endpoint with optional live OCI support.
- VCN inventory endpoint with optional live OCI support.
- Subnet inventory endpoint with optional live OCI support.
- Gateway inventory endpoint with optional live OCI support.
- Route table inventory endpoint with optional live OCI support.
- Security list inventory endpoint with optional live OCI support.
- Topology graph endpoint derived from live OCI inventory.
- Initial security posture endpoint for broad ingress exposure.
- OCI client factory abstraction.
- OCI Terraform baseline.
- Ansible bootstrap.
- Documentation set.
- Manual local validation commands.
- Planned API reference.
- Planned data model.
- Deployment checklist.
- Manual release process.
- English-only product specification.

## Not Yet Implemented

- React production frontend.
- OCI SDK collectors beyond the current identity, preflight, and initial network inventory services.
- Scheduler.
- Cache.
- Authentication UI.
- Persisted application configuration.
- Automated application tests.

## Recommended Next Work

1. Add NSG inventory endpoint.
2. Add route table issue detection.
3. Add richer security posture scoring.
4. Add OCI response normalization for all collectors.
5. Add dashboard filtering by configured compartment and region.
6. Replace static HTML deployment with frontend build artifact deployment.
7. Add remote Terraform state.
8. Add HTTPS and private access pattern.
9. Add Meridian self-monitoring.
