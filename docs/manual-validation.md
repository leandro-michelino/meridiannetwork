# Manual Validation

This repository intentionally avoids GitHub Actions and other Git-hosted automation. Validation is manual and local.

## Terraform

```bash
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

## Ansible

```bash
ansible-galaxy collection install -r ansible/requirements.yml
printf '[meridian]\nlocalhost ansible_connection=local\n' > /tmp/meridian_inventory
ansible-playbook --syntax-check -i /tmp/meridian_inventory ansible/playbooks/bootstrap.yml
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
```

There should be no `.github/workflows` files.

