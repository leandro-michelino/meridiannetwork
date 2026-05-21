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

output "vcn_id" {
  description = "VCN OCID."
  value       = oci_core_vcn.meridian.id
}

output "subnet_id" {
  description = "Public subnet OCID."
  value       = oci_core_subnet.public.id
}

