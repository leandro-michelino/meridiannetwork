# Deployment Checklist

Use this checklist before deploying Meridian into an OCI tenancy.

## Repository

- Confirm the repository has no GitHub Actions or automation workflows.
- Confirm all validation is run locally.
- Confirm no secrets are committed.
- Confirm no Terraform state files are committed.
- Confirm no generated Ansible inventory is committed.

## OCI

- Confirm tenancy OCID.
- Confirm compartment OCID.
- Confirm target region.
- Confirm home region and any additional active regions.
- Confirm monitored compartment OCIDs for `MERIDIAN_COMPARTMENT_IDS`.
- Confirm admin source CIDR blocks.
- Confirm SSH public key path.
- Confirm OCI CLI profile.
- Confirm required permissions for network and compute creation.
- Confirm runtime policies grant compartment discovery and Virtual Networking read access.

## Terraform

- Copy `terraform/terraform.tfvars.example`.
- Populate `terraform/terraform.tfvars`.
- Run `make tf-init`.
- Run `make tf-validate`.
- Run `make tf-plan`.
- Review all resources in the plan.
- Confirm public exposure is intentional.
- Run `make tf-apply`.

## Ansible

- Run `make inventory`.
- Run `make ping`.
- Run `make deploy`.
- Confirm Nginx is running.
- Confirm the dashboard URL responds.
- Run the dashboard `Validate access` button and confirm it has no failed checks.
- Confirm `GET /api/preflight` returns `pass` before relying on live inventory.

## Security

- Restrict `admin_cidr_blocks`.
- Disable broad ingress.
- Keep IAM policy creation disabled until reviewed.
- Prefer instance principal for production.
- Add HTTPS before broad exposure.
- Consider a private subnet, VPN, Bastion, or private load balancer for production.

## Post-Deployment

- Save Terraform outputs in the deployment notes.
- Record the instance public IP.
- Record the dashboard URL.
- Record the source commit.
- Record any manual changes made in OCI.
