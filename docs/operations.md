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

7. Validate runtime OCI access:

```bash
curl http://<dashboard-host>/api/preflight
```

8. Confirm deployed revision metadata:

```bash
curl http://<dashboard-host>/api/version
curl http://<dashboard-host>/version.json
```

Both responses should reference the commit you deployed and report `dirty: false` when the deployment was run from a
clean working tree.

## Manual Validation

Before changing infrastructure or pushing repository updates, run the checks in [manual-validation.md](manual-validation.md).

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

Rebuild only the dashboard artifact:

```bash
make frontend-build
```

Run the backend locally:

```bash
make backend-install
make backend-test
make dashboard-e2e
make backend-run
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
- Use `enable_nat_gateway = true` when you want default outbound traffic routed through NAT while keeping public ingress scoped.
- Use `security_action_archive_enabled = true` only when the tenancy should retain security finding action history in Object Storage.
- Keep `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=false` unless the customer has explicitly approved dashboard-driven
  VCN Flow Log setup and the runtime principal has the matching OCI Logging and capture-filter permissions.

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
- Check headers with `curl -I http://<dashboard-host>/index.html`; the dashboard shell should not be cached.

If the API service is unavailable after deployment:

- SSH to the host.
- Check `sudo systemctl status meridian-api`.
- Check `sudo journalctl -u meridian-api -n 100`.
- Check `/opt/meridian/config/meridian.env`.
- Confirm Nginx can reach `127.0.0.1:8080`.

If live inventory is empty or the preflight fails:

- Confirm `MERIDIAN_ENABLE_LIVE_OCI=true`.
- Confirm `MERIDIAN_TENANCY_OCID` is set.
- Confirm `MERIDIAN_COMPARTMENT_IDS` contains the monitored compartment OCIDs, or that tenancy-root inventory is intended.
- Confirm the instance principal dynamic group matches the Meridian Compute instance.
- Confirm the dynamic group has `inspect compartments` and `read virtual-network-family` policies.

If a customer is troubleshooting VM-to-VM or subnet-to-subnet reachability:

- Use Connectivity Check first. It runs OCI Network Path Analyzer for the exact source, destination, protocol, and port
  without enabling VCN Flow Logs.
- Review the forward/return status, likely blockers, next actions, and hop table for denied security actions or missing
  route targets.
- Enable VCN Flow Logs only if packet-level evidence is still needed after path analysis.
- Confirm the runtime principal can `read log-content`.
- Use the dashboard Traffic Telemetry button only after setting `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true`.
- Confirm VCN Flow Logs are enabled for the selected VCN before querying flow records.
- Confirm the source and destination IPs are private IPs visible from VNIC inventory.
- Allow a short delay for newly enabled VCN Flow Logs to start producing records.

If the deployment badge or version endpoints show an old revision:

- Run `git status --short --branch` locally and commit or discard intentional local changes before deploying.
- Run `make deploy` again so Ansible rebuilds `frontend/dist/` and copies the backend to the VM.
- Compare `curl http://<dashboard-host>/api/version` with `curl http://<dashboard-host>/version.json`.
- If either response reports `dirty: true`, the deploy was built from a worktree with uncommitted changes.
