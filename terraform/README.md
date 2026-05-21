# Terraform

This directory creates the initial OCI infrastructure for Meridian.

## Resources

- VCN.
- Public subnet.
- Internet gateway.
- Route table.
- Security list.
- Compute instance.
- Optional dynamic group and IAM policy.

## Files

- `versions.tf`: Terraform and provider constraints.
- `provider.tf`: OCI provider configuration.
- `variables.tf`: Input variables.
- `locals.tf`: Derived names and policy rendering.
- `data.tf`: Availability domain and image lookup.
- `network.tf`: VCN, subnet, gateway, routing, security list.
- `compute.tf`: OCI Compute host.
- `identity.tf`: Optional dynamic group and policy.
- `outputs.tf`: IPs, URL, SSH command, resource IDs.
- `terraform.tfvars.example`: Example environment configuration.

## Usage

```bash
make tf-init
make tf-plan
make tf-apply
```

Or directly:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform plan
terraform -chdir=terraform apply
```

## Manual Validation

```bash
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

## Required Variables

- `tenancy_ocid`
- `compartment_ocid`
- `region`
- `admin_cidr_blocks`

## Important Defaults

- `project_name = "meridian"`
- `environment = "dev"`
- `vcn_cidr = "10.42.0.0/16"`
- `public_subnet_cidr = "10.42.10.0/24"`
- `instance_shape = "VM.Standard.E5.Flex"`
- `instance_ocpus = 1`
- `instance_memory_gb = 8`
- `create_identity_policies = false`

When `create_identity_policies = true`, the default runtime policy grants `read virtual-network-family` so Meridian can
list VCNs, subnets, gateways, route tables, security lists, DRGs, and network security groups during preflight and live
inventory.

## Production Notes

- Use remote state before team usage.
- Restrict admin CIDRs.
- Review IAM statements before setting `create_identity_policies = true`.
- Consider private subnet plus load balancer or VPN for production.
