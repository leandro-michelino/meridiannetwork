# Changelog

## Unreleased

- Add FastAPI backend foundation.
- Add health and readiness endpoints.
- Add regions and compartments API endpoints.
- Add VCN and subnet inventory API endpoints.
- Add gateway inventory API endpoint.
- Add route table and security list inventory API endpoints.
- Add route issue API endpoint and dashboard panel for route table analysis.
- Add Network Security Group inventory API endpoint, topology nodes, dashboard panel, and security posture checks.
- Add topology graph API endpoint and dashboard graph rendering from live inventory relationships.
- Add draggable, keyboard-navigable topology nodes with persisted browser layout positions.
- Add OCI preflight API endpoint and dashboard top-bar validation button for IAM, region, compartment, and network read validation.
- Add configurable monitored compartment IDs through `MERIDIAN_COMPARTMENT_IDS`.
- Add initial security posture API endpoint.
- Refresh the static dashboard prototype to consume implemented API endpoints with demo fallback data.
- Add OCI client factory abstraction.
- Update default runtime IAM policy to use read-only Virtual Networking access for live inventory.
- Add deployment options documentation covering VM, serverless container, Functions, and OKE patterns.
- Add backend tests and local backend commands.
- Update Ansible to deploy the backend as a systemd service behind Nginx.
- Standardize repository documentation in English.
- Add planned API reference.
- Add planned data model.
- Add deployment checklist.
- Add manual validation guide.
- Add manual release process.
- Add repository security policy.
- Add repository text attributes.
- Translate the static dashboard prototype labels to English.
- Improve the static dashboard inventory UX with compartment context, subnet access wording, real OCI resource IDs, and a pinned home-region expander.
- Replace the dashboard refresh button with a 5-second background refresh loop for live API mode.
- Add dashboard expanders across topology, security, gateway, route, security-list, and VCN/subnet inventory panels.
- Preserve the no GitHub Actions policy.

## 2026-05-21

- Add Terraform baseline for OCI networking and compute.
- Add Ansible host bootstrap.
- Add static dashboard prototype.
- Add architecture, operations, security, roadmap, and remote audit documentation.
- Remove GitHub Actions workflow and document manual validation policy.
