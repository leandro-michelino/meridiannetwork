# Ansible

This directory configures the OCI Compute host created by Terraform.

## What It Does

- Installs base packages.
- Creates Meridian runtime directories.
- Writes a Meridian environment file.
- Publishes the current static dashboard HTML.
- Copies and installs the Meridian FastAPI backend.
- Configures a `meridian-api` systemd service.
- Configures Nginx.
- Opens SSH, HTTP, and HTTPS in firewalld.
- Enables Nginx.

## Inventory

Inventory is generated from Terraform outputs:

```bash
make inventory
```

The generated file is:

```text
ansible/inventory/oci.ini
```

It is ignored by Git because it contains environment-specific IP addresses.

## Usage

```bash
make ansible-requirements
make ping
make deploy
```

## Manual Validation

```bash
printf '[meridian]\nlocalhost ansible_connection=local\n' > /tmp/meridian_inventory
ansible-playbook --syntax-check -i /tmp/meridian_inventory ansible/playbooks/bootstrap.yml
```

## Main Playbook

```text
ansible/playbooks/bootstrap.yml
```

## Backend Service

The deployed API service is:

```text
meridian-api.service
```

Nginx proxies these backend paths to the service:

- `/api/`
- `/healthz`
- `/readyz`
- `/docs`
- `/redoc`
- `/openapi.json`

## Variables

Main variables are in:

```text
ansible/group_vars/oci.yml
```

The playbook also loads this file explicitly through `vars_files`.
