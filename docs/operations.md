# Operations Runbook

## Bootstrap

1. Create a Terraform variables file:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

2. Fill in tenancy, compartment, region, admin CIDRs, and SSH key path.

3. Initialize Terraform:

```bash
make tf-init
```

4. Review the plan:

```bash
make tf-plan
```

5. Apply infrastructure:

```bash
make tf-apply
```

6. Configure the host:

```bash
make deploy
```

## Day-2 Commands

Generate Ansible inventory again:

```bash
make inventory
```

Check SSH and Python reachability:

```bash
make ping
```

Re-run host configuration:

```bash
make deploy
```

Destroy the baseline:

```bash
make tf-destroy
```

## Terraform State

The scaffold currently uses local Terraform state.

Before production use:

- Store state in a controlled backend.
- Enable locking if the chosen backend supports it.
- Restrict state access because state can contain sensitive metadata.

OCI Object Storage can be used through an S3-compatible backend pattern, or state can be stored in another approved Terraform backend.

## Access Model

The initial host is reachable through public IP and security list rules controlled by `admin_cidr_blocks`.

Operational recommendations:

- Use `/32` public IP CIDRs for administrators where possible.
- Prefer VPN, Bastion, private load balancer, or private subnet for production.
- Add HTTPS before exposing the dashboard beyond a trusted network.

## Troubleshooting

If Terraform cannot authenticate:

- Check `oci_profile`.
- Check `OCI_CONFIG_FILE` if using a non-default path.
- Confirm tenancy, user, fingerprint, key path, and region in the OCI config.

If Ansible cannot connect:

- Run `terraform -chdir=terraform output ssh_command`.
- Confirm the instance public IP is reachable.
- Confirm the private key matches `ssh_public_key_path`.
- Confirm local outbound SSH is allowed.
- Confirm security list allows port `22` from your source CIDR.

If Nginx does not serve the dashboard:

- Run `make ping` first.
- Re-run `make deploy`.
- SSH to the host and check `sudo systemctl status nginx`.
- Check `/var/log/nginx/meridian_error.log`.

