# Meridian Network

Meridian is a self-hosted OCI Network Monitor for consolidated network observability across compartments and regions.

The product vision is captured in [Meridian_OCI_Network_Monitor.md](Meridian_OCI_Network_Monitor.md). This repository also includes the first deployable infrastructure baseline using Terraform and Ansible.

## Why Meridian

Meridian is meant for teams that need a practical, tenant-local view of OCI networking without starting from a heavy platform rollout.
It runs close to the environment it observes, uses OCI-native authentication patterns, and focuses on the questions that usually come up during operations, reviews, migrations, and customer workshops:

- Which regions and compartments are actually in scope?
- Which VCNs, subnets, gateways, route tables, security lists, and NSGs exist?
- Where are public routes, broad ingress rules, or zero-resource regions?
- Is the runtime identity allowed to read the networking data the dashboard needs?
- What exact version of the dashboard/API is deployed on the VM?

It is intentionally small enough to understand and adapt, but structured enough to be deployed repeatedly with Terraform and Ansible.

## Use Cases

- **OCI network discovery**: build a fast inventory of VCNs, subnets, gateways, route tables, security lists, and NSGs across selected regions.
- **Multi-region visibility**: avoid noisy global views by selecting the exact regions you want to inspect.
- **Security posture review**: highlight public SSH/RDP exposure, broad public egress, public web ingress, and related network findings.
- **Route and topology analysis**: understand how VCN resources connect through gateways, routes, and subnet associations.
- **Migration and landing-zone reviews**: validate what exists before or after a migration, region expansion, or landing-zone rollout.
- **Customer demos and workshops**: use the `/demodata` mode for safe demonstrations, then switch to live OCI mode for real environments.
- **Operational validation**: use preflight checks to confirm instance principal access, tenancy configuration, compartment scope, and required OCI read permissions.
- **Deployment traceability**: confirm the deployed Git revision through `/api/version` and `/version.json`.

## Interested in Implementing It?

If you are interested in implementing, adapting, or discussing Meridian for an OCI environment, contact:

**Leandro Michelino, Oracle ACE**

`leandro.michelino@oracle.com`

## Current Repository Status

- Remote: `https://github.com/leandro-michelino/meridiannetwork.git`
- Branch: `main`
- Initial remote content reviewed: `LICENSE`
- Local baseline added: Terraform, Ansible, docs, and helper scripts.

## What Is Included

- Terraform for OCI VCN, public subnet, internet gateway, route table, security list, and Compute host.
- Optional OCI dynamic group and IAM policy for instance principal access.
- FastAPI backend foundation with health, readiness, preflight, regions, and compartments endpoints.
- Buildable frontend artifact for the API-aware dashboard with fallback demo data, 5-second live refresh, compartment-aware inventory, draggable topology, subnet access labels, NSG context, resource IDs, expanders, and pinned home-region navigation.
- Dashboard top-bar access validation button for runtime IAM, region, compartment, and network read validation.
- Ansible bootstrap to configure Oracle Linux with Nginx, Podman-ready packages, firewall rules, cache-safe dashboard publishing, deployment version metadata, and the backend API service.
- Inventory generation from Terraform outputs.
- Documentation for architecture, operations, security/IAM, API design, data model, roadmap, release process, and remote audit.
- Manual local validation commands for Terraform and Ansible.

## Repository Layout

```text
.
├── ansible/                # Host configuration and dashboard publishing
├── backend/                # FastAPI backend foundation
├── docs/                   # Architecture, operations, security, API, roadmap
├── frontend/               # Dashboard build scripts and generated dist output
├── scripts/                # Local helper scripts
├── terraform/              # OCI infrastructure as code
├── Makefile                # Common local commands
├── Meridian_OCI_Network_Monitor.md
└── oci_network_monitor_dashboard_v2.html
```

## Prerequisites

- Terraform 1.6 or newer.
- Ansible 2.15 or newer.
- Node.js 20 or newer for the frontend build script.
- OCI credentials configured through an OCI CLI profile, environment variables, or another supported OCI provider auth mode.
- An SSH public key available locally, for example `~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`.
- OCI permissions to create networking, compute, and optionally IAM resources.

## Quick Start

Copy the example variables file:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit `terraform/terraform.tfvars` with:

- `tenancy_ocid`
- `compartment_ocid`
- `region`
- `admin_cidr_blocks`
- `ssh_public_key_path`

Initialize and validate:

```bash
make tf-init
make tf-plan
```

Create the OCI baseline:

```bash
make tf-apply
```

Configure the host and publish the built dashboard artifact:

```bash
make deploy
```

Open the URL printed by Terraform output `app_url`.

The deployment publishes `/version.json` and the backend exposes `GET /api/version`; both include the Git revision deployed to the VM.

## Common Commands

```bash
make help
make tf-init
make tf-validate
make tf-plan
make tf-apply
make inventory
make ping
make frontend-build
make deploy
make tf-destroy
make backend-install
make backend-test
make backend-run
```

## Validation Policy

This repository intentionally does not use GitHub Actions or other Git automation. Run validation locally before pushing changes.

Use [docs/manual-validation.md](docs/manual-validation.md) as the source of truth for manual checks.

## Backend Development

Install backend development dependencies:

```bash
make backend-install
```

Run tests:

```bash
make backend-test
```

Run the API locally:

```bash
make backend-run
```

Local endpoints:

- `GET /healthz`
- `GET /readyz`
- `GET /api/version`
- `GET /api/preflight`
- `GET /api/regions/available`
- `GET /api/regions/active`
- `GET /api/compartments`
- `GET /api/vcns`
- `GET /api/subnets`
- `GET /api/gateways`
- `GET /api/route-tables`
- `GET /api/route-issues`
- `GET /api/security-lists`
- `GET /api/network-security-groups`
- `GET /api/topology`
- `GET /api/security/posture`
- `GET /docs`

## OCI Authentication

Terraform uses the OCI provider and defaults to `config_file_profile = "DEFAULT"`.

To use another profile, set `oci_profile` in `terraform/terraform.tfvars`.

If your OCI config file is not in the default location, export:

```bash
export OCI_CONFIG_FILE=/path/to/config
```

For runtime inventory scope, set monitored compartments explicitly when you do not want the API to use the tenancy root
as the default compartment scope:

```bash
export MERIDIAN_COMPARTMENT_IDS=ocid1.compartment.oc1..example,ocid1.compartment.oc1..example2
```

## IAM Model

`create_identity_policies` is disabled by default because IAM policy creation usually requires tenancy-level privileges.

When enabled, Terraform creates:

- A dynamic group matching Compute instances in the application compartment.
- A read-oriented policy intended for instance principal access to network observability data.

The deployed API exposes `GET /api/preflight`, and the dashboard includes a top-bar `Validate access` button to validate
runtime authentication, compartment discovery, configured regions, monitored compartments, and required networking read
permissions on demand.

Review [docs/security-and-iam.md](docs/security-and-iam.md) before enabling IAM creation in a shared tenancy.

## Documentation

- [Architecture](docs/architecture.md)
- [Operations Runbook](docs/operations.md)
- [Security and IAM](docs/security-and-iam.md)
- [API Reference](docs/api-reference.md)
- [Data Model](docs/data-model.md)
- [Deployment Checklist](docs/deployment-checklist.md)
- [Deployment Options](docs/deployment-options.md)
- [Manual Validation](docs/manual-validation.md)
- [Module Map](docs/module-map.md)
- [Roadmap](docs/roadmap.md)
- [Release Process](docs/release-process.md)
- [Remote Audit](docs/remote-audit.md)
- [Security Policy](SECURITY.md)
- [Backend README](backend/README.md)
- [Terraform README](terraform/README.md)
- [Ansible README](ansible/README.md)

## First Production Hardening Items

- Move Terraform state to a remote backend.
- Replace direct public HTTP with HTTPS through an OCI Load Balancer or reverse proxy certificate.
- Narrow `admin_cidr_blocks` to VPN or office IP ranges.
- Continue splitting the dashboard source into frontend modules as it grows.
- Add monitoring alarms for the Meridian host itself.
