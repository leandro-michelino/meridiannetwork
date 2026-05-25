# Changelog

## Unreleased

- Split the frontend build into build-info and HTML artifact helper modules.
- Add dashboard deployment badge backed by injected frontend metadata and backend version metadata.
- Scope coverage and exports to the currently selected regions to avoid noisy global views.
- Add saved region views in the Regions menu.
- Add topology quick filters for public subnets, internet paths, and findings.
- Add security finding workflow filter and broader OCI Console links in findings/action history.
- Refresh README, project status, release, operations, deployment, roadmap, and architecture documentation.
- Replace architecture diagrams with plain ASCII runtime, build/deploy, topology, and selected-region data-flow diagrams.
- Clean stale documentation references to the removed product specification and old single-file/no-build dashboard wording.
- Fix print CSS to target the current `.topbar` selector.
- Restore Terraform wiring for managed workload compartments, optional NAT egress, default security list lockdown, externally managed IAM metadata, and optional Object Storage action-history archive.
- Add async per-region collection pipeline with `ThreadPoolExecutor` (4 workers).
- Add in-memory snapshot cache with configurable TTL and persistent on-disk snapshot cache.
- Add per-region collection status panel: collecting spinner, ready/failed/no-resources badges,
  resource counts, duration, and relative timestamps with exponential backoff polling (3–15 s).
- Add `RegionService.list_active()` and `/api/regions/active` endpoint for configured-region scope.
- Fix topology DRG edges: regional gateways (vcn_id=None) now use a region-anchor fallback so they
  appear in the graph and in VCN focus mode.
- Fix topology VCN focus mode: DRGs are synthesised onto the selected VCN so edges render correctly.
- Add topology hint when VCN focus mode returns only the VCN node with no children.
- Add markdownlint configuration (compact table style, 160-char line limit for prose).
- Rewrite architecture documentation with accurate ASCII diagrams for runtime, deployment, and
  async data-flow.
- Rewrite API reference with full endpoint documentation and `collection` response schema.
- Rewrite module map with implemented/planned status across all feature categories.
- Update roadmap to mark Phases 0–2 as complete.
- Update project status to reflect current implementation.
- Remove stale product specification document (superseded by docs/).
- Fix Ansible environment template: remove bogus `MERIDIAN_APP_PORT`, add all missing variables
  including snapshot TTL, snapshot dir, resource search scope, and OCI profile.
- Fix Ansible group vars: correct home region, add all new variable defaults.
- Harden systemd service unit: add restart limits, journal logging, and syslog identifier.
- Add snapshot directory to Ansible bootstrap directory-creation loop.

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
