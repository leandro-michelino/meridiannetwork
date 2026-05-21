# Contributing

## Development Principles

- Keep infrastructure changes small and reviewable.
- Prefer read-only OCI permissions unless write behavior is explicitly required.
- Do not commit local credentials, state files, generated inventory, or private keys.
- Update documentation whenever workflow, architecture, or IAM assumptions change.

## Validation

Run these before opening a pull request:

```bash
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

For Ansible:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
printf '[meridian]\nlocalhost ansible_connection=local\n' > /tmp/meridian_inventory
ansible-playbook --syntax-check -i /tmp/meridian_inventory ansible/playbooks/bootstrap.yml
```

## Commit Style

Use clear, direct commit messages:

```text
Add OCI Terraform baseline
Document IAM model
Configure Ansible bootstrap
```

