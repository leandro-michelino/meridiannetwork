# Manual Validation

This repository intentionally avoids GitHub Actions and other Git-hosted automation. Validation is manual and local.

## Terraform

```bash
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

Use `make tf-validate` when the local Terraform directory has already been initialized.

## Ansible

```bash
ansible-galaxy collection install -r ansible/requirements.yml
printf '[meridian]\nlocalhost ansible_connection=local\n' > /tmp/meridian_inventory
ansible-playbook --syntax-check -i /tmp/meridian_inventory ansible/playbooks/bootstrap.yml
```

## Frontend Build

```bash
make frontend-build
```

Expected output is a regenerated ignored `frontend/dist/` directory containing `index.html` and `version.json`.

## Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
make backend-install
make backend-test
ruff check backend
python -m compileall -q backend/app
```

## Dashboard Browser E2E

```bash
make dashboard-e2e
```

The E2E tests require Playwright and a local Chrome/Chromium browser. Set `MERIDIAN_E2E_BROWSER` when Chrome is not in
one of the default macOS locations.

## Human Connectivity Check

Use this when you want to test the same path a customer would click through in the dashboard.

In the browser:

- Open the dashboard in API mode.
- Go to **Connectivity Check**.
- Enter the exact source and destination. Use IPs for the quickest smoke test, or paste a resource OCID from the
  inventory datalist when you want OCI to analyze a named resource.
- Pick the protocol, port, and direction.
- Click **Check connectivity**.
- Confirm the result panel says `no logs enabled` and that **Enable telemetry** was not triggered automatically.

From the terminal, the same check looks like this:

```bash
curl -sS -X POST http://<dashboard-host>/api/connectivity/check \
  -H 'Content-Type: application/json' \
  -d '{
    "source": {"type": "ip_address", "value": "10.42.10.142"},
    "destination": {"type": "ip_address", "value": "8.8.8.8"},
    "protocol": "TCP",
    "destination_port": 443,
    "bidirectional": false,
    "region": "me-abudhabi-1"
  }' | jq '{status, reachable, message, findings, next_actions, cost_impact, work_request_id}'
```

If a region is slow or returns `running`, try the same request with another active region:

```bash
curl -sS http://<dashboard-host>/api/regions/active | jq '.[].id'
```

For big tenancies, also check the compartment count:

```bash
curl -sS http://<dashboard-host>/api/compartments | jq 'length'
```

If the response says Network Path Analyzer needs a compartment-count service-limit increase, that is a real OCI
condition. Meridian should show the short, useful message and still report `cost_impact: no_flow_logs_enabled`.

## Traffic Telemetry Cost Gate

Run these before any demo where cost control matters:

```bash
curl -sS http://<dashboard-host>/api/traffic/telemetry/status
curl -sS 'http://<dashboard-host>/api/traffic/telemetry/status?check_vcns=true'
curl -sS -X POST http://<dashboard-host>/api/traffic/telemetry/enable \
  -H 'Content-Type: application/json' \
  -d '{"vcn_ids":["dummy"]}'
```

Expected behavior for the default safe configuration:

- The first status call is lightweight.
- The coverage call can scan VCN Flow Log state only when explicitly requested.
- The enable call returns `403 TRAFFIC_ENABLEMENT_DISABLED` unless
  `MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true`.
- When telemetry is allowed, enable responses include `expires_at`; values longer than 60 minutes are clamped.
- The dashboard should let the user disable Meridian-created telemetry after the troubleshooting window.
- Expired leases are swept from `/opt/meridian/data/traffic-telemetry-leases.json` after Meridian disables/deletes the
  Flow Log resource.

Optional local API smoke test:

```bash
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/api/version
curl http://127.0.0.1:8080/api/preflight
curl http://127.0.0.1:8080/api/vcns
curl http://127.0.0.1:8080/api/subnets
curl http://127.0.0.1:8080/api/gateways
curl http://127.0.0.1:8080/api/route-tables
curl http://127.0.0.1:8080/api/route-issues
curl http://127.0.0.1:8080/api/security-lists
curl http://127.0.0.1:8080/api/network-security-groups
curl http://127.0.0.1:8080/api/topology
curl http://127.0.0.1:8080/api/security/posture
```

## Inventory Script

```bash
printf '%s\n' '{"instance_public_ip":{"value":"203.0.113.20"},"instance_private_ip":{"value":"10.42.10.10"},"ssh_user":{"value":"opc"}}' | python3 scripts/render_inventory.py
```

Expected output:

```ini
[meridian]
meridian-oci ansible_host=203.0.113.20 ansible_user=opc private_ip=10.42.10.10

[meridian:vars]
ansible_python_interpreter=/usr/bin/python3
```

## Repository Checks

```bash
find .github -maxdepth 3 -type f -print 2>/dev/null || true
git status --short --branch
git ls-tree -r --name-only origin/main
git diff --check
```

There should be no `.github/workflows` files.

## Deployment Smoke Test

After `make deploy`, verify the published VM is serving the same clean revision from the frontend and backend:

```bash
curl http://<dashboard-host>/version.json
curl http://<dashboard-host>/api/version
curl -I http://<dashboard-host>/index.html
```

Both version endpoints should report the deployed Git revision and `dirty: false`. The `index.html` and `version.json`
responses should include no-cache headers so browsers do not retain an older dashboard shell.
