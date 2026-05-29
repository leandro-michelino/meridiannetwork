locals {
  name_prefix   = "${var.project_name}-${var.environment}"
  is_flex_shape = can(regex("Flex$", var.instance_shape))
  resource_tags = merge(
    {
      project = var.project_name
      managed = "terraform"
    },
    var.freeform_tags
  )
  parent_compartment_ocid = coalesce(var.parent_compartment_ocid, var.tenancy_ocid)
  workload_compartment_ocid = (
    var.create_meridian_compartment
    ? oci_identity_compartment.meridian[0].id
    : var.compartment_ocid
  )
  workload_compartment_name = (
    var.create_meridian_compartment
    ? oci_identity_compartment.meridian[0].name
    : coalesce(var.parent_compartment_name, "external-compartment")
  )

  admin_tcp_ports = [22, 80, 443]
  admin_tcp_rules = flatten([
    for cidr in var.admin_cidr_blocks : [
      for port in local.admin_tcp_ports : {
        cidr = cidr
        port = port
      }
    ]
  ])

  dynamic_group_name = "${local.name_prefix}-instances"
  effective_instance_principal_dynamic_group_name = (
    var.create_identity_policies
    ? local.dynamic_group_name
    : var.external_instance_principal_dynamic_group_name
  )
  rendered_identity_policy_statements = [
    for statement in concat(
      var.identity_policy_statements,
      var.enable_traffic_flow_log_management_policy ? var.traffic_flow_log_management_policy_statements : []
    ) :
    replace(statement, "{dynamic_group_name}", local.dynamic_group_name)
  ]
  rendered_external_traffic_flow_log_policy_statements = [
    for statement in var.traffic_flow_log_management_policy_statements :
    replace(statement, "{dynamic_group_name}", local.effective_instance_principal_dynamic_group_name)
    if local.effective_instance_principal_dynamic_group_name != null
  ]
  instance_principal_dynamic_group = (
    var.create_identity_policies
    ? oci_identity_dynamic_group.meridian[0].name
    : (
      var.external_instance_principal_dynamic_group_name != null
      ? "External dynamic group ${var.external_instance_principal_dynamic_group_name}"
      : "Not managed by Terraform"
    )
  )
  instance_principal_policy = (
    var.create_identity_policies
    ? oci_identity_policy.meridian[0].name
    : (
      var.external_instance_principal_policy_name != null
      ? var.external_instance_principal_policy_name
      : "Not managed by Terraform"
    )
  )
  oracle_services_cidr = data.oci_core_services.oracle_services_network.services[0].cidr_block
  egress_rules = var.enable_nat_gateway ? [
    {
      destination      = "0.0.0.0/0"
      destination_type = "CIDR_BLOCK"
      protocol         = "6"
      port             = 443
    },
    {
      destination      = local.oracle_services_cidr
      destination_type = "SERVICE_CIDR_BLOCK"
      protocol         = "6"
      port             = 443
    }
    ] : [
    {
      destination      = "0.0.0.0/0"
      destination_type = "CIDR_BLOCK"
      protocol         = "all"
      port             = null
    }
  ]
  route_rules = concat(
    [
      {
        destination       = "0.0.0.0/0"
        destination_type  = "CIDR_BLOCK"
        network_entity_id = var.enable_nat_gateway ? oci_core_nat_gateway.meridian[0].id : oci_core_internet_gateway.meridian.id
      }
    ],
    var.enable_nat_gateway ? [
      for cidr in var.admin_cidr_blocks : {
        destination       = cidr
        destination_type  = "CIDR_BLOCK"
        network_entity_id = oci_core_internet_gateway.meridian.id
      }
    ] : []
  )
  security_action_archive_bucket_name = coalesce(
    var.security_action_archive_bucket_name,
    "${local.name_prefix}-action-history"
  )
  security_action_archive_prefix = trimsuffix(
    coalesce(var.security_action_archive_prefix, "${var.project_name}/security-actions/"),
    "/"
  )
}
