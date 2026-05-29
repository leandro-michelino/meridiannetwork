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

If a customer is troubleshooting VM-to-VM, subnet-to-subnet, or VM-to-service reachability:

- Start with **Connectivity Check**. Put in the exact source, destination, protocol, port, and direction, then click
  **Check connectivity**.
- This runs OCI Network Path Analyzer. It does not enable VCN Flow Logs, does not collect packets, and the API response
  should say `cost_impact: no_flow_logs_enabled`.
- If the result is `blocked`, read the first finding and the hop table before changing anything. Most real issues are
  still the classics: source egress blocked, destination ingress blocked, route table missing a target, DRG path missing,
  or return traffic going a different way.
- If the result is `running`, the UI is protecting the browser and proxy from a long OCI work request. Wait a moment and
  run the check again, preferably with the most specific region and compartment you know.
- If the result mentions "more compartments than the current OCI Network Path Analyzer service limit", the app is not
  inventing that. Very large tenancies can hit OCI Network Path Analyzer's compartment-count limit. Try the exact target
  region if you were using a broad scope, but expect to request an NPA service-limit increase if the tenancy itself is
  over the limit.
- Enable VCN Flow Logs only if packet-level evidence is still needed after path analysis.
- Use **Enable telemetry** only for the selected VCN and only after setting
  `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true`.
- Confirm the runtime principal can `read log-content`, and if the dashboard is allowed to create telemetry, confirm it
  also has the optional Flow Log management policy.
- When the customer has enough evidence, click **Disable telemetry** for that same VCN. This keeps the investigation
  useful without leaving surprise log-ingestion costs behind.
- Allow a short delay for newly enabled VCN Flow Logs to start producing records.

Useful live checks from your laptop:

```bash
curl http://<dashboard-host>/api/regions/active
curl http://<dashboard-host>/api/compartments | jq 'length'
curl http://<dashboard-host>/api/traffic/telemetry/status
curl 'http://<dashboard-host>/api/traffic/telemetry/status?check_vcns=true'
```

The lightweight telemetry status call should not scan every VCN. Use `check_vcns=true` only when you really want the
coverage check.

If the deployment badge or version endpoints show an old revision:

- Run `git status --short --branch` locally and commit or discard intentional local changes before deploying.
- Run `make deploy` again so Ansible rebuilds `frontend/dist/` and copies the backend to the VM.
- Compare `curl http://<dashboard-host>/api/version` with `curl http://<dashboard-host>/version.json`.
- If either response reports `dirty: true`, the deploy was built from a worktree with uncommitted changes.
