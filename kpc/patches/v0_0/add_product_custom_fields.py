# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Extend the standard Item doctype with petroleum product properties.

Per the architecture, "Product" is not a new doctype - it is the standard
ERPNext Item extended with the density/temperature attributes needed for
volumetric conversion (see kpc.petroleum_operations.utils.calculate_vcf).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "petroleum_properties_tab",
			"fieldtype": "Tab Break",
			"label": "Petroleum Properties",
			"insert_after": "inspection_required_before_delivery",
		},
		{
			"fieldname": "density_at_15c",
			"fieldtype": "Float",
			"label": "Density at 15C (kg/L)",
			"precision": "4",
			"insert_after": "petroleum_properties_tab",
			"description": "Reference density used for VCF/standard-volume calculations.",
		},
		{
			"fieldname": "reference_temperature_c",
			"fieldtype": "Float",
			"label": "Reference Temperature (C)",
			"precision": "2",
			"default": "15",
			"insert_after": "density_at_15c",
		},
		{
			"fieldname": "column_break_petroleum_1",
			"fieldtype": "Column Break",
			"insert_after": "reference_temperature_c",
		},
		{
			"fieldname": "api_gravity",
			"fieldtype": "Float",
			"label": "API Gravity",
			"precision": "2",
			"insert_after": "column_break_petroleum_1",
		},
		{
			"fieldname": "is_petroleum_product",
			"fieldtype": "Check",
			"label": "Is Petroleum Product",
			"insert_after": "api_gravity",
		},
	]
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch)
