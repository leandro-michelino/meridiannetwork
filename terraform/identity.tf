resource "oci_identity_compartment" "meridian" {
  count          = var.create_meridian_compartment ? 1 : 0
  compartment_id = local.parent_compartment_ocid
  name           = var.meridian_compartment_name
  description    = "Compartment for Meridian Network resources."
  enable_delete  = true
  freeform_tags  = local.resource_tags
}

resource "oci_identity_dynamic_group" "meridian" {
  count          = var.create_identity_policies ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = local.dynamic_group_name
  description    = "Meridian OCI Network Monitor instances"
  matching_rule  = "ALL {instance.compartment.id = '${local.workload_compartment_ocid}'}"
}

resource "oci_identity_policy" "meridian" {
  count          = var.create_identity_policies ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-instance-principal-policy"
  description    = "Read-only OCI access for Meridian network observability"
  statements     = local.rendered_identity_policy_statements
}

resource "oci_identity_policy" "traffic_flow_log_management" {
  count = (
    var.enable_traffic_flow_log_management_policy && !var.create_identity_policies
    ? 1
    : 0
  )

  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-traffic-flow-log-management"
  description    = "Optional OCI access for Meridian dashboard-driven VCN Flow Log setup"
  statements     = local.rendered_external_traffic_flow_log_policy_statements
}
