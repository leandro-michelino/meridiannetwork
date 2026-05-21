# Project Status

Date: 2026-05-21

## Current Stage

Backend foundation scaffold.

## Available Now

- Product specification document.
- Static dashboard prototype.
- FastAPI backend foundation.
- Health and readiness endpoints.
- Regions endpoints.
- Compartments endpoint with optional live OCI support.
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
- OCI SDK collectors beyond the initial identity/compartment service.
- Scheduler.
- Cache.
- Authentication UI.
- Persisted application configuration.
- Automated application tests.

## Recommended Next Work

1. Add VCN inventory endpoint.
2. Add gateway inventory endpoint.
3. Add OCI pagination helpers and response normalization for all collectors.
4. Replace static HTML deployment with frontend build artifact deployment.
5. Containerize backend and frontend.
6. Add remote Terraform state.
7. Add HTTPS and private access pattern.
8. Add Meridian self-monitoring.
