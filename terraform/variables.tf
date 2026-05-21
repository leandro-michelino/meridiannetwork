variable "tenancy_ocid" {
  description = "OCI tenancy OCID."
  type        = string
}

variable "compartment_ocid" {
  description = "OCI compartment OCID where Meridian infrastructure will be created."
  type        = string
}

variable "region" {
  description = "OCI region, for example eu-frankfurt-1 or eu-madrid-1."
  type        = string
}

variable "oci_profile" {
  description = "OCI CLI profile used by the Terraform provider."
  type        = string
  default     = "DEFAULT"
}

variable "project_name" {
  description = "Project name used for OCI resource names."
  type        = string
  default     = "meridian"
}

variable "environment" {
  description = "Environment label used for OCI resource names."
  type        = string
  default     = "dev"
}

variable "availability_domain_name" {
  description = "Optional availability domain name. If null, the first AD is used."
  type        = string
  default     = null
}

variable "vcn_cidr" {
  description = "CIDR block for the Meridian VCN."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet."
  type        = string
  default     = "10.42.10.0/24"
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks allowed to reach SSH, HTTP, and HTTPS."
  type        = list(string)
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key installed on the OCI instance."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_user" {
  description = "Default SSH user for the selected image."
  type        = string
  default     = "opc"
}

variable "instance_shape" {
  description = "OCI Compute shape for the Meridian host."
  type        = string
  default     = "VM.Standard.E5.Flex"
}

variable "instance_ocpus" {
  description = "OCPUs for flexible shapes."
  type        = number
  default     = 1
}

variable "instance_memory_gb" {
  description = "Memory in GB for flexible shapes."
  type        = number
  default     = 8
}

variable "boot_volume_size_gb" {
  description = "Boot volume size in GB."
  type        = number
  default     = 80
}

variable "image_operating_system" {
  description = "Operating system image family."
  type        = string
  default     = "Oracle Linux"
}

variable "image_operating_system_version" {
  description = "Operating system image version."
  type        = string
  default     = "9"
}

variable "app_port" {
  description = "Local application port behind Nginx."
  type        = number
  default     = 8080
}

variable "create_identity_policies" {
  description = "Create OCI dynamic group and IAM policy for instance principal access."
  type        = bool
  default     = false
}

variable "identity_policy_statements" {
  description = "IAM policy statements used when create_identity_policies is true."
  type        = list(string)
  default = [
    "allow dynamic-group {dynamic_group_name} to inspect compartments in tenancy",
    "allow dynamic-group {dynamic_group_name} to inspect virtual-network-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to inspect instance-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to read metrics in tenancy",
    "allow dynamic-group {dynamic_group_name} to read logging-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to read alarms in tenancy"
  ]
}

variable "freeform_tags" {
  description = "Freeform tags applied to OCI resources."
  type        = map(string)
  default = {
    project = "meridian"
    managed = "terraform"
  }
}
