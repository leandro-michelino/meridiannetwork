resource "oci_core_vcn" "meridian" {
  compartment_id = local.workload_compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "${local.name_prefix}-vcn"
  dns_label      = "meridian"
  freeform_tags  = local.resource_tags
}

resource "oci_core_internet_gateway" "meridian" {
  compartment_id = local.workload_compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-igw"
  enabled        = true
  freeform_tags  = local.resource_tags
}

resource "oci_core_nat_gateway" "meridian" {
  count          = var.enable_nat_gateway ? 1 : 0
  compartment_id = local.workload_compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-natgw"
  block_traffic  = false
  freeform_tags  = local.resource_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = local.workload_compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-public-rt"
  freeform_tags  = local.resource_tags

  dynamic "route_rules" {
    for_each = local.route_rules

    content {
      destination       = route_rules.value.destination
      destination_type  = route_rules.value.destination_type
      network_entity_id = route_rules.value.network_entity_id
    }
  }
}

resource "oci_core_default_security_list" "meridian" {
  manage_default_resource_id = oci_core_vcn.meridian.default_security_list_id
  display_name               = "${local.name_prefix}-default-sl"
  freeform_tags              = local.resource_tags
}

resource "oci_core_security_list" "public" {
  compartment_id = local.workload_compartment_ocid
  vcn_id         = oci_core_vcn.meridian.id
  display_name   = "${local.name_prefix}-public-sl"
  freeform_tags  = local.resource_tags

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

  dynamic "egress_security_rules" {
    for_each = local.egress_rules

    content {
      protocol         = egress_security_rules.value.protocol
      destination      = egress_security_rules.value.destination
      destination_type = egress_security_rules.value.destination_type

      dynamic "tcp_options" {
        for_each = egress_security_rules.value.port == null ? [] : [egress_security_rules.value.port]

        content {
          min = tcp_options.value
          max = tcp_options.value
        }
      }
    }
  }
}

resource "oci_core_subnet" "public" {
  cidr_block                 = var.public_subnet_cidr
  compartment_id             = local.workload_compartment_ocid
  vcn_id                     = oci_core_vcn.meridian.id
  display_name               = "${local.name_prefix}-public-subnet"
  dns_label                  = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  freeform_tags              = local.resource_tags
}
