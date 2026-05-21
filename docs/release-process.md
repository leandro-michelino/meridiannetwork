# Release Process

Meridian currently uses manual repository validation and manual release notes. No GitHub Actions, Git hooks, or Git-hosted automation should be added without explicit approval.

## Manual Release Steps

1. Review the working tree.
2. Run manual validation.
3. Update `CHANGELOG.md`.
4. Commit with a clear message.
5. Push to `origin/main`.
6. Confirm the remote head.

## Commands

```bash
git status --short --branch
terraform -chdir=terraform fmt -recursive -check
terraform -chdir=terraform validate
ansible-playbook --syntax-check -i /tmp/meridian_inventory ansible/playbooks/bootstrap.yml
git log --oneline --decorate --max-count=5
git push origin main
git ls-remote --heads origin main
```

## Policy

- No GitHub Actions.
- No Git-hosted automation.
- No committed secrets.
- No committed Terraform state.
- No committed generated inventory.
- Documentation updates should ship with behavior changes.

