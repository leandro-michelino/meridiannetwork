resource "oci_identity_dynamic_group" "meridian" {
  count          = var.create_identity_policies ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = local.dynamic_group_name
  description    = "Meridian OCI Network Monitor instances"
  matching_rule  = "ALL {instance.compartment.id = '${var.compartment_ocid}'}"
}

resource "oci_identity_policy" "meridian" {
  count          = var.create_identity_policies ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-instance-principal-policy"
  description    = "Read-only OCI access for Meridian network observability"
  statements     = local.rendered_identity_policy_statements
}

