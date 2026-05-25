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
