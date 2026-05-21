# Security and IAM

## Baseline Principles

- Keep OCI permissions read-oriented.
- Avoid `manage` permissions unless a future feature explicitly needs changes to OCI resources.
- Keep SSH and HTTP access restricted by source CIDR.
- Do not commit `terraform.tfvars`, OCI config files, private keys, or generated inventories.
- Use instance principal for production runtime access to OCI APIs.

## Terraform Variables That Affect Security

- `admin_cidr_blocks`: controls who can reach SSH, HTTP, and HTTPS.
- `create_identity_policies`: creates tenancy-level IAM resources when enabled.
- `identity_policy_statements`: defines runtime OCI permissions for Meridian.
- `ssh_public_key_path`: controls SSH key installed on the instance.

## Default IAM Policy Intent

When enabled, the default policy statements are intended to allow the Meridian instance to inspect or read:

- Compartments.
- Virtual network family.
- Instance family.
- Monitoring metrics.
- Logging family.
- Alarms.

These defaults are intentionally read-oriented and should be reviewed per tenancy.

## Recommended Production Adjustments

- Replace public access with private access where possible.
- Put the host behind HTTPS.
- Use OCI Bastion or VPN for SSH access.
- Keep dynamic group matching scoped to the application compartment.
- Consider separate compartments for dev, demo, and production.
- Enable OS Management or another approved patching process.
- Add backups or image-based recovery once application state exists.

## Secrets Handling

Ignored by Git:

- `terraform/terraform.tfvars`
- `*.tfstate`
- `ansible/inventory/oci.ini`
- `.env`
- `ansible/vault.yml`

Use Ansible Vault, OCI Vault, or environment variables for future secrets.

