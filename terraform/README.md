# Terraform

This directory creates the initial OCI infrastructure for Meridian.

## Resources

- VCN.
- Public subnet.
- Internet gateway.
- Optional NAT gateway for restricted outbound access.
- Route table.
- Security list.
- Managed default security list lockdown.
- Compute instance.
- Optional workload compartment.
- Optional dynamic group and IAM policy.
- Optional Object Storage bucket for security finding action history.

## Files

- `versions.tf`: Terraform and provider constraints.
- `provider.tf`: OCI provider configuration.
- `variables.tf`: Input variables.
- `locals.tf`: Derived names and policy rendering.
- `data.tf`: Availability domain and image lookup.
- `network.tf`: VCN, subnet, gateway, routing, security list.
- `compute.tf`: OCI Compute host.
- `identity.tf`: Optional dynamic group and policy.
- `object_storage.tf`: Optional action-history archive bucket and lifecycle policy.
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
- `compartment_ocid`, unless `create_meridian_compartment = true`
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
- `create_meridian_compartment = false`
- `enable_nat_gateway = false`
- `security_action_archive_enabled = false`
- `enable_traffic_flow_log_management_policy = false`

When `create_identity_policies = true`, the default runtime policy grants read-oriented inventory and logging access so
Meridian can list VCNs, subnets, gateways, route tables, security lists, DRGs, network security groups, and existing VCN
Flow Log records during preflight and live inventory.

Set `enable_traffic_flow_log_management_policy = true` only when the runtime principal should be allowed to create the
log groups, log content, and capture filters needed by the dashboard Traffic Telemetry enablement button.

When `create_identity_policies = false`, use `external_instance_principal_dynamic_group_name` and
`external_instance_principal_policy_name` to document the externally managed IAM objects in Terraform outputs.

## Production Notes

- Use remote state before team usage.
- Restrict admin CIDRs.
- Review IAM statements before setting `create_identity_policies = true`.
- Consider private subnet plus load balancer or VPN for production.
