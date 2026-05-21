# Ansible

This directory configures the OCI Compute host created by Terraform.

## What It Does

- Installs base packages.
- Creates Meridian runtime directories.
- Writes a Meridian environment file.
- Publishes the current static dashboard HTML.
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

## Main Playbook

```text
ansible/playbooks/bootstrap.yml
```

## Variables

Main variables are in:

```text
ansible/group_vars/oci.yml
```

The playbook also loads this file explicitly through `vars_files`.

