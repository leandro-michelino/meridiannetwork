# Security Policy

## Supported Status

Meridian is currently in foundation scaffold stage. It is not yet a production application.

## Reporting Security Issues

Do not open public issues with secrets, tenancy details, private IP maps, or customer-specific topology.

Report security-sensitive findings directly to the repository owner through an approved private channel.

## Sensitive Data

Never commit:

- OCI config files.
- OCI private keys.
- SSH private keys.
- Terraform state.
- `terraform.tfvars`.
- Generated Ansible inventory.
- Vault files.
- Customer topology exports.

## Infrastructure Policy

- Keep OCI permissions read-oriented by default.
- Use narrow admin CIDR blocks.
- Prefer instance principal for production runtime access.
- Use HTTPS before exposing the dashboard beyond a trusted network.
- Prefer VPN, Bastion, or private access for production deployments.

## Automation Policy

This repository intentionally does not use GitHub Actions or Git-hosted automation. Run validation manually and locally.

