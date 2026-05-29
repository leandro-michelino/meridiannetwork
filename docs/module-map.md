# Module Map

Status key: **Implemented** · *Planned*

## Core Operations

| Feature                                                              | Status              |
| -------------------------------------------------------------------- | ------------------- |
| Live VCN / Subnet / Gateway inventory                                | **Implemented**     |
| Route table inventory and rule listing                               | **Implemented**     |
| Route issue analysis (blackhole, duplicate default, invalid entity)  | **Implemented**     |
| Security List and NSG inventory with rule summaries                  | **Implemented**     |
| Interactive topology graph (Overview / Layers / VCN focus)           | **Implemented**     |
| Security posture panel (risky ingress/egress rule detection)         | **Implemented**     |
| Exact-resource Connectivity Check with OCI Network Path Analyzer     | **Implemented**     |
| Cost-gated VCN Flow Logs evidence collection                         | **Implemented**     |
| Reversible selected-VCN telemetry enable/disable workflow             | **Implemented**     |
| 60-minute max telemetry lease with automatic cleanup                  | **Implemented**     |
| Async per-region collection with status panel                        | **Implemented**     |
| Persistent on-disk snapshot cache                                    | **Implemented**     |
| OCI runtime preflight checks                                         | **Implemented**     |
| Deployment version metadata                                          | **Implemented**     |
| CSV exports for inventory, completeness, and security posture        | **Implemented**     |
| Optional Object Storage archive for security action history          | **Implemented**     |
| VCN Flow Logs viewer                                                 | **Implemented**     |
| Inter-region latency                                                 | *Planned*           |
| VNIC and Compute top consumers                                       | *Planned*           |
| DR readiness panel                                                   | *Planned*           |

## Navigation and Scope

| Feature                                                    | Status          |
| ---------------------------------------------------------- | --------------- |
| Region selector with multi-region support                  | **Implemented** |
| Saved region views                                         | **Implemented** |
| Compartment discovery and filter                           | **Implemented** |
| Per-region collection status (Ready / Collecting / Failed / No resources) | **Implemented** |
| Selected-region coverage panel                             | **Implemented** |
| Compartment-tag-based scope filter                         | *Planned*       |

## Security and Governance

| Feature                                                                | Status          |
| ---------------------------------------------------------------------- | --------------- |
| Security posture score and findings                                    | **Implemented** |
| Risky Security List rule detection (SSH/RDP/all-protocol from 0.0.0.0/0) | **Implemented** |
| NSG risky rule detection                                               | **Implemented** |
| Finding workflow filter and action history                             | **Implemented** |
| OCI Audit change feed                                                  | *Planned*       |
| Exportable security reports                                            | *Planned*       |

## Network Deep Dives

| Feature                            | Status    |
| ---------------------------------- | --------- |
| DRG inventory (listed under gateways) | **Implemented** |
| Exact source/destination path analysis | **Implemented** |
| DRG route inspector                | *Planned* |
| OKE network health                 | *Planned* |
| Cost-aware egress                  | *Planned* |
| Synthetic health checks            | *Planned* |
| Load Balancer health panel         | *Planned* |
| Private DNS visibility             | *Planned* |
| FastConnect / IPSec VPN            | *Planned* |

## Operations

| Feature                                    | Status    |
| ------------------------------------------ | --------- |
| PDF and CSV export                         | *Planned* |
| OCI Notifications                          | *Planned* |
| Slack / Teams / email notification targets | *Planned* |

## Intelligence Layer

| Feature                            | Status    |
| ---------------------------------- | --------- |
| Alarm explainer (GenAI)            | *Planned* |
| Natural language Flow Logs query   | *Planned* |
| Security risk narrative            | *Planned* |
| Change-feed impact analysis        | *Planned* |
| DR readiness summary               | *Planned* |

## Implemented API Endpoints

```text
GET /healthz
GET /readyz
GET /api/version
GET /api/preflight
GET /api/regions/available
GET /api/regions/active
GET /api/compartments
GET /api/identity/context
GET /api/dashboard
GET /api/dashboard/completeness
GET /api/vcns
GET /api/subnets
GET /api/gateways
GET /api/route-tables
GET /api/route-issues
GET /api/security-lists
GET /api/network-security-groups
GET /api/topology
GET /api/security/posture
GET /api/security/finding-actions
POST /api/security/finding-actions
POST /api/connectivity/check
GET /api/traffic/telemetry/status
POST /api/traffic/telemetry/enable
POST /api/traffic/telemetry/disable
GET /api/traffic/flows
GET /api/export/security-posture.csv
GET /api/export/inventory.csv
GET /api/export/completeness.csv
```
