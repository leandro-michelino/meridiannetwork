variable "tenancy_ocid" {
  description = "OCI tenancy OCID."
  type        = string
}

variable "compartment_ocid" {
  description = "Existing OCI compartment OCID where Meridian infrastructure will be created when create_meridian_compartment is false."
  type        = string
  default     = null
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

variable "parent_compartment_ocid" {
  description = "Parent compartment OCID used when create_meridian_compartment is true. Defaults to the tenancy OCID."
  type        = string
  default     = null
}

variable "parent_compartment_name" {
  description = "Friendly parent compartment name used only in deployment metadata."
  type        = string
  default     = null
}

variable "create_meridian_compartment" {
  description = "Create a dedicated workload compartment for Meridian resources."
  type        = bool
  default     = false
}

variable "meridian_compartment_name" {
  description = "Name of the managed Meridian workload compartment."
  type        = string
  default     = "Meridian"
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

variable "enable_nat_gateway" {
  description = "Create a NAT gateway and route default outbound traffic through it while keeping public ingress restricted."
  type        = bool
  default     = false
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
    "allow dynamic-group {dynamic_group_name} to read virtual-network-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to inspect instance-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to read metrics in tenancy",
    "allow dynamic-group {dynamic_group_name} to read logging-family in tenancy",
    "allow dynamic-group {dynamic_group_name} to read alarms in tenancy"
  ]
}

variable "external_instance_principal_dynamic_group_name" {
  description = "Name of an externally managed dynamic group used when create_identity_policies is false."
  type        = string
  default     = null
}

variable "external_instance_principal_policy_name" {
  description = "Name of an externally managed IAM policy used when create_identity_policies is false."
  type        = string
  default     = null
}

variable "instance_principal_access_group_name" {
  description = "Optional human access group name documented in the deployment card."
  type        = string
  default     = null
}

variable "security_action_archive_enabled" {
  description = "Create an Object Storage bucket for security finding action history archive."
  type        = bool
  default     = false
}

variable "security_action_archive_bucket_name" {
  description = "Optional Object Storage bucket name for security action archive. Defaults to <project>-<environment>-action-history."
  type        = string
  default     = null
}

variable "security_action_archive_prefix" {
  description = "Object name prefix used for security action archive objects."
  type        = string
  default     = null
}

variable "security_action_archive_retention_days" {
  description = "Retention period, in days, for security action archive objects."
  type        = number
  default     = 365
}

variable "freeform_tags" {
  description = "Additional freeform tags applied to OCI resources. Project and managed tags are added automatically."
  type        = map(string)
  default     = {}
}
