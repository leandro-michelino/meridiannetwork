# Architecture

## Goal

Meridian centralizes OCI network observability into one operational dashboard.

The first repository baseline focuses on deployment foundations:

- OCI network and Compute host.
- Runtime bootstrap with Ansible.
- Static dashboard publishing.
- Future-ready IAM model for instance principal authentication.

The product design adds API aggregation, scheduled collection, cache, charts, topology, alarms, flow logs, DR readiness, load balancer visibility, Private DNS visibility, DRG route inspection, and OCI GenAI-assisted explanations.

## High-Level Components

```text
OCI Tenancy
  |
  +-- VCN / Subnet / Gateways / DRG / VPN / FastConnect
  +-- Monitoring / Logging / Audit / DNS / Load Balancer APIs
  |
  +-- Meridian Host
        |
        +-- Nginx
        +-- Static dashboard
        +-- Future FastAPI backend
        +-- Future scheduler and cache
```

## Current Deployment Topology

Terraform creates:

- One VCN.
- One public subnet.
- One internet gateway.
- One route table.
- One security list limited by `admin_cidr_blocks`.
- One Compute instance using Oracle Linux.
- Optional dynamic group and IAM policy.

Ansible configures:

- Base packages.
- Runtime user and directories.
- Nginx virtual host.
- Firewall rules for SSH, HTTP, and HTTPS.
- Static dashboard copied to the web root.

## Future Application Topology

The intended production application is:

- Frontend: React dashboard.
- Backend: Python FastAPI.
- Scheduler: APScheduler or Celery.
- Cache: Redis or OCI Cache.
- Auth to OCI: instance principal in production, API key in development.
- Runtime: VM with Podman, containerized services, or OKE later.

## Main Data Sources

- OCI Monitoring metrics.
- OCI Logging and Logging Analytics.
- OCI Audit.
- OCI Networking APIs.
- OCI Load Balancer and Network Load Balancer APIs.
- OCI Private DNS APIs.
- OCI DRG, FastConnect, and IPSec APIs.
- OCI Price List API for egress estimates.
- OCI Generative AI for explanation and query assistance.

## Security Boundary

The Meridian host should run with the minimum OCI read permissions required for network observability. Write actions should remain out of scope until explicitly needed.

The current public subnet approach is for a practical initial deployment. A hardened production pattern should place Meridian behind a private load balancer, bastion, VPN, or identity-aware access layer.

