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
- `enable_traffic_flow_log_management_policy`: adds optional `manage` permissions used only when customers allow the
  dashboard to create VCN Flow Logs from the Traffic Telemetry panel.
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

The current dashboard needs read access to Virtual Networking because it lists VCNs, subnets, route tables, security
lists, Internet Gateways, NAT Gateways, Service Gateways, DRGs, and Network Security Groups during preflight. `manage`
permissions are not required for the runtime dashboard.

## Runtime Preflight

The backend exposes:

```text
GET /api/preflight
```

The preflight endpoint validates:

- Live OCI mode and runtime authentication mode.
- `MERIDIAN_TENANCY_OCID`.
- Home region plus configured active regions.
- `MERIDIAN_COMPARTMENT_IDS`, or tenancy root when no explicit monitored compartments are configured.
- OCI SDK and signer creation.
- Compartment discovery permission.
- Virtual Networking read access for the resource types used by the dashboard, including NSG rules when NSGs exist.

The dashboard also exposes this checklist through the topbar `Validate access` button.

## Minimum Runtime Policies

For production instance-principal access, create a dynamic group that matches the Meridian Compute instance and grant
read-only inventory permissions. The Terraform baseline can create this when `create_identity_policies = true`.

Tenancy-wide example:

```text
allow dynamic-group <meridian-dynamic-group> to inspect compartments in tenancy
allow dynamic-group <meridian-dynamic-group> to read virtual-network-family in tenancy
allow dynamic-group <meridian-dynamic-group> to inspect instance-family in tenancy
allow dynamic-group <meridian-dynamic-group> to read metrics in tenancy
allow dynamic-group <meridian-dynamic-group> to read logging-family in tenancy
allow dynamic-group <meridian-dynamic-group> to read log-content in tenancy
allow dynamic-group <meridian-dynamic-group> to read alarms in tenancy
```

Compartment-scoped example:

```text
allow dynamic-group <meridian-dynamic-group> to inspect compartments in tenancy
allow dynamic-group <meridian-dynamic-group> to read virtual-network-family in compartment <network-compartment-name>
```

Use compartment-scoped policies when the customer does not want tenancy-wide network inventory. Set
`MERIDIAN_COMPARTMENT_IDS` to a comma-separated list of monitored compartment OCIDs so the API and preflight validate
those compartments directly.

## Service Enablement Notes

- Network inventory requires OCI Networking APIs and `read virtual-network-family`.
- Compartment names require Identity compartment discovery through `inspect compartments`.
- Traffic Telemetry reads VCN Flow Logs through OCI Logging Search and needs `read log-content`.
- The Traffic Telemetry enablement button is disabled unless `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true`.
  If customers want the dashboard to create the required log group, service logs, and capture filters, the runtime
  principal also needs the optional management policy statements from `enable_traffic_flow_log_management_policy`.
- Metrics and alarms permissions are reserved for planned modules; they are included in Terraform defaults so the policy
  can be reviewed before those modules are enabled.
- Config-file authentication requires a valid OCI config profile and API key on the host.
- Instance principal authentication requires the Compute instance to match a dynamic group and for that dynamic group to
  have the policy statements above.

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

## Automation Policy

Do not add GitHub Actions, Git-hosted workflows, or other repository automation without explicit approval. Security and infrastructure validation should be run locally using the manual validation guide.
