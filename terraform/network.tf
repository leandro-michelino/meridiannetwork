resource "oci_core_vcn" "meridian" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "${local.name_prefix}-vcn"
  dns_label      = "meridian"
  freeform_tags  = var.freeform_tags
}

resource "oci_core_internet_gateway" "meridian" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-igw"
  enabled        = true
  freeform_tags  = var.freeform_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-public-rt"
  freeform_tags  = var.freeform_tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.meridian.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-public-sl"
  freeform_tags  = var.freeform_tags

  dynamic "ingress_security_rules" {
    for_each = local.admin_tcp_rules

    content {
      protocol = "6"
      source   = ingress_security_rules.value.cidr

      tcp_options {
        min = ingress_security_rules.value.port
        max = ingress_security_rules.value.port
      }
    }
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_subnet" "public" {
  cidr_block                 = var.public_subnet_cidr
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.meridian.id
  display_name               = "${local.name_prefix}-public-subnet"
  dns_label                  = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  freeform_tags              = var.freeform_tags
}

