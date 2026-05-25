resource "oci_objectstorage_bucket" "security_action_archive" {
  count          = var.security_action_archive_enabled ? 1 : 0
  compartment_id = local.workload_compartment_ocid
  namespace      = data.oci_objectstorage_namespace.current.namespace
  name           = local.security_action_archive_bucket_name
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  freeform_tags  = local.resource_tags
}

resource "oci_objectstorage_object_lifecycle_policy" "security_action_archive" {
  count     = var.security_action_archive_enabled ? 1 : 0
  namespace = data.oci_objectstorage_namespace.current.namespace
  bucket    = oci_objectstorage_bucket.security_action_archive[0].name

  rules {
    name        = "${local.security_action_archive_bucket_name}-retention"
    action      = "DELETE"
    target      = "objects"
    is_enabled  = true
    time_amount = var.security_action_archive_retention_days + 1
    time_unit   = "DAYS"

    object_name_filter {
      inclusion_prefixes = [local.security_action_archive_prefix]
      inclusion_patterns = []
      exclusion_patterns = []
    }
  }
}
