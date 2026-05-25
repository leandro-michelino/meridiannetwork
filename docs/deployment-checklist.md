# Deployment Checklist

Use this checklist before deploying Meridian into an OCI tenancy.

## Repository

- Confirm the repository has no GitHub Actions or automation workflows.
- Confirm all validation is run locally.
- Confirm no secrets are committed.
- Confirm no Terraform state files are committed.
- Confirm no generated Ansible inventory is committed.
- Confirm `frontend/dist/`, E2E screenshots, and cache directories are not committed.
- Run `make frontend-build`, `make backend-test`, and `make dashboard-e2e`.

## OCI

- Confirm tenancy OCID.
- Confirm compartment OCID, or confirm `create_meridian_compartment` and `parent_compartment_ocid`.
- Confirm target region.
- Confirm home region and any additional active regions.
- Confirm monitored compartment OCIDs for `MERIDIAN_COMPARTMENT_IDS`.
- Confirm admin source CIDR blocks.
- Confirm SSH public key path.
- Confirm OCI CLI profile.
- Confirm required permissions for network and compute creation.
- Confirm runtime policies grant compartment discovery and Virtual Networking read access.
- Confirm whether NAT egress and the security action Object Storage archive should be enabled.

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
- Confirm `GET /api/version` returns the expected Git revision.
- Confirm `/version.json` returns the same frontend revision.
- Confirm both version endpoints report `dirty: false` after deploying from a clean worktree.
- Confirm `/index.html` and `/version.json` are served with no-cache headers.

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
- Record the `/api/version` and `/version.json` responses.
- Record any manual changes made in OCI.
