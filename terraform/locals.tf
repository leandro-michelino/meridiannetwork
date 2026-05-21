locals {
  name_prefix   = "${var.project_name}-${var.environment}"
  is_flex_shape = can(regex("Flex$", var.instance_shape))

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
  rendered_identity_policy_statements = [
    for statement in var.identity_policy_statements :
    replace(statement, "{dynamic_group_name}", local.dynamic_group_name)
  ]
}

