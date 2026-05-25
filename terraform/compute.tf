resource "oci_core_instance" "meridian" {
  availability_domain = coalesce(
    var.availability_domain_name,
    data.oci_identity_availability_domains.ads.availability_domains[0].name
  )
  compartment_id = local.workload_compartment_ocid
  display_name   = "${local.name_prefix}-host"
  shape          = var.instance_shape
  freeform_tags  = local.resource_tags

  dynamic "shape_config" {
    for_each = local.is_flex_shape ? [1] : []

    content {
      ocpus         = var.instance_ocpus
      memory_in_gbs = var.instance_memory_gb
    }
  }

  create_vnic_details {
    assign_public_ip = true
    display_name     = "${local.name_prefix}-primary-vnic"
    hostname_label   = "meridian"
    subnet_id        = oci_core_subnet.public.id
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.oracle_linux.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_gb
  }

  metadata = {
    ssh_authorized_keys = file(pathexpand(var.ssh_public_key_path))
  }
}
