# Data Model

This document captures the planned normalized data model for Meridian.

## Resource Identity

Every OCI resource should normalize to:

```text
id
name
display_name
resource_type
region
compartment_id
compartment_name
lifecycle_state
time_created
freeform_tags
defined_tags
console_url
```

## NetworkResource

Used for VCNs, subnets, gateways, route tables, DRGs, and related network objects.

```text
id
name
resource_type
region
compartment_id
vcn_id
cidr_blocks
lifecycle_state
relationships
risk_summary
```

## TopologyGraph

Used by the dashboard to draw discovered OCI network relationships.

```text
nodes[]
  id
  name
  resource_type
  region
  compartment_id
  vcn_id
  lifecycle_state
  metadata

edges[]
  id
  source_id
  target_id
  relationship
  metadata
```

## MetricPoint

```text
resource_id
namespace
metric_name
dimensions
timestamp
value
unit
statistic
interval
```

## AlarmSummary

```text
id
name
severity
status
region
compartment_id
resource_id
metric_query
triggered_at
duration_seconds
console_url
```

## FlowLogRecord

```text
timestamp
region
compartment_id
vcn_id
subnet_id
source_ip
source_port
destination_ip
destination_port
protocol
action
bytes
packets
log_source
```

## SecurityFinding

```text
id
severity
rule_type
resource_id
resource_name
region
compartment_id
description
evidence
recommendation
console_url
```

## HealthcheckResult

```text
check_id
target
check_type
source_region
destination_region
timestamp
status
latency_ms
packet_loss_percent
error_message
```

## CostEstimate

```text
resource_id
region
period_start
period_end
egress_gb
unit_price
estimated_cost
currency
```
