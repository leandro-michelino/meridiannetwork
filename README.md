# Meridian Network

Meridian is a self-hosted OCI Network Monitor for consolidated network observability across compartments and regions.

The product vision is captured in [Meridian_OCI_Network_Monitor.md](Meridian_OCI_Network_Monitor.md). This repository also includes the first deployable infrastructure baseline using Terraform and Ansible.

## Current Repository Status

- Remote: `https://github.com/leandro-michelino/meridiannetwork.git`
- Branch: `main`
- Initial remote content reviewed: `LICENSE`
- Local baseline added: Terraform, Ansible, docs, and helper scripts.

## What Is Included

- Terraform for OCI VCN, public subnet, internet gateway, route table, security list, and Compute host.
- Optional OCI dynamic group and IAM policy for instance principal access.
- Ansible bootstrap to configure Oracle Linux with Nginx, Podman-ready packages, firewall rules, and the static dashboard.
- Inventory generation from Terraform outputs.
- Documentation for architecture, operations, security/IAM, roadmap, and remote audit.
- Manual local validation commands for Terraform and Ansible.

## Repository Layout

```text
.
├── ansible/                # Host configuration and dashboard publishing
├── docs/                   # Architecture, operations, security, roadmap
├── scripts/                # Local helper scripts
├── terraform/              # OCI infrastructure as code
├── Makefile                # Common local commands
├── Meridian_OCI_Network_Monitor.md
└── oci_network_monitor_dashboard_v2.html
```

## Prerequisites

- Terraform 1.6 or newer.
- Ansible 2.15 or newer.
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

Configure the host and publish the static dashboard:

```bash
make deploy
```

Open the URL printed by Terraform output `app_url`.

## Common Commands

```bash
make help
make tf-init
make tf-validate
make tf-plan
make tf-apply
make inventory
make ping
make deploy
make tf-destroy
```

## Validation Policy

This repository intentionally does not use GitHub Actions or other Git automation. Run validation locally before pushing changes.

## OCI Authentication

Terraform uses the OCI provider and defaults to `config_file_profile = "DEFAULT"`.

To use another profile, set `oci_profile` in `terraform/terraform.tfvars`.

If your OCI config file is not in the default location, export:

```bash
export OCI_CONFIG_FILE=/path/to/config
```

## IAM Model

`create_identity_policies` is disabled by default because IAM policy creation usually requires tenancy-level privileges.

When enabled, Terraform creates:

- A dynamic group matching Compute instances in the application compartment.
- A read-oriented policy intended for instance principal access to network observability data.

Review [docs/security-and-iam.md](docs/security-and-iam.md) before enabling IAM creation in a shared tenancy.

## Documentation

- [Architecture](docs/architecture.md)
- [Operations Runbook](docs/operations.md)
- [Security and IAM](docs/security-and-iam.md)
- [Module Map](docs/module-map.md)
- [Roadmap](docs/roadmap.md)
- [Remote Audit](docs/remote-audit.md)
- [Terraform README](terraform/README.md)
- [Ansible README](ansible/README.md)

## First Production Hardening Items

- Move Terraform state to a remote backend.
- Replace direct public HTTP with HTTPS through an OCI Load Balancer or reverse proxy certificate.
- Narrow `admin_cidr_blocks` to VPN or office IP ranges.
- Split application backend/frontend once the FastAPI and React code are added.
- Add monitoring alarms for the Meridian host itself.
