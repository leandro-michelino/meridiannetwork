output "instance_public_ip" {
  description = "Public IP address of the Meridian host."
  value       = oci_core_instance.meridian.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the Meridian host."
  value       = oci_core_instance.meridian.private_ip
}

output "ssh_user" {
  description = "SSH user for Ansible."
  value       = var.ssh_user
}

output "ssh_command" {
  description = "Convenience SSH command."
  value       = "ssh ${var.ssh_user}@${oci_core_instance.meridian.public_ip}"
}

output "app_url" {
  description = "Meridian dashboard URL."
  value       = "http://${oci_core_instance.meridian.public_ip}"
}

output "tenancy_ocid" {
  description = "OCI tenancy OCID used by this deployment."
  value       = var.tenancy_ocid
}

output "region" {
  description = "OCI region used by this deployment."
  value       = var.region
}

output "workload_compartment_ocid" {
  description = "Compartment OCID where Meridian workload resources are deployed."
  value       = local.workload_compartment_ocid
}

output "workload_compartment_name" {
  description = "Compartment name where Meridian workload resources are deployed."
  value       = local.workload_compartment_name
}

output "vcn_id" {
  description = "VCN OCID."
  value       = oci_core_vcn.meridian.id
}

output "subnet_id" {
  description = "Public subnet OCID."
  value       = oci_core_subnet.public.id
}

output "admin_cidr_blocks" {
  description = "CIDR blocks allowed to reach Meridian ingress ports."
  value       = var.admin_cidr_blocks
}

output "access_boundary" {
  description = "Summary of ingress and egress boundaries configured by Terraform."
  value = {
    ingress_cidr_blocks      = var.admin_cidr_blocks
    ingress_tcp_ports        = local.admin_tcp_ports
    nat_gateway_egress       = var.enable_nat_gateway
    nat_gateway_id           = var.enable_nat_gateway ? oci_core_nat_gateway.meridian[0].id : null
    internet_egress_cidrs    = var.enable_nat_gateway ? [] : ["0.0.0.0/0"]
    internet_egress_tcp_443  = var.enable_nat_gateway ? "0.0.0.0/0 via NAT Gateway" : null
    oracle_services_egress   = var.enable_nat_gateway ? local.oracle_services_cidr : null
    oracle_services_tcp_port = var.enable_nat_gateway ? 443 : null
  }
}

output "instance_principal_iam_source" {
  description = "IAM source used for instance principal runtime access."
  value = {
    dynamic_group = local.instance_principal_dynamic_group
    policy        = local.instance_principal_policy
    traffic_flow_log_management_policy = (
      length(oci_identity_policy.traffic_flow_log_management) > 0
      ? oci_identity_policy.traffic_flow_log_management[0].name
      : (
        var.enable_traffic_flow_log_management_policy && var.create_identity_policies
        ? oci_identity_policy.meridian[0].name
        : "disabled"
      )
    )
  }
}

output "security_action_archive" {
  description = "Object Storage archive target for security finding actions."
  value = {
    enabled        = var.security_action_archive_enabled
    namespace      = var.security_action_archive_enabled ? data.oci_objectstorage_namespace.current.namespace : null
    bucket         = var.security_action_archive_enabled ? oci_objectstorage_bucket.security_action_archive[0].name : null
    prefix         = var.security_action_archive_enabled ? "${local.security_action_archive_prefix}/" : null
    retention_days = var.security_action_archive_retention_days
  }
}

output "meridian_deployment_card" {
  description = "Human-readable deployment summary."
  value       = <<EOT
Meridian Network deployment
---------------------------
Dashboard          : http://${oci_core_instance.meridian.public_ip}
SSH                : ssh ${var.ssh_user}@${oci_core_instance.meridian.public_ip}
Region             : ${var.region}
Compartment        : ${local.workload_compartment_name} (${local.workload_compartment_ocid})
VCN                : ${oci_core_vcn.meridian.display_name} (${var.vcn_cidr})
Subnet             : ${oci_core_subnet.public.display_name} (${var.public_subnet_cidr})
Allowed ingress    : ${join(", ", var.admin_cidr_blocks)} on TCP ${join(", ", [for port in local.admin_tcp_ports : tostring(port)])}
NAT egress         : ${var.enable_nat_gateway ? "enabled for TCP 443 default outbound" : "disabled"}
Internet egress    : ${var.enable_nat_gateway ? "none configured beyond NAT TCP 443" : "0.0.0.0/0"}
Oracle Services    : ${var.enable_nat_gateway ? "${local.oracle_services_cidr} on TCP 443" : "not separately restricted"}
IAM principal      : ${local.instance_principal_dynamic_group}
IAM policy         : ${local.instance_principal_policy}
Traffic telemetry  : ${var.enable_traffic_flow_log_management_policy ? "management policy enabled" : "management policy disabled"}
IAM access group   : ${coalesce(var.instance_principal_access_group_name, "not specified")}
Action archive     : ${var.security_action_archive_enabled ? "${local.security_action_archive_bucket_name}/${local.security_action_archive_prefix}/" : "disabled"}
EOT
}
