# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Extend standard ERPNext Stock doctypes for the Golden Thread - the same
pattern as add_accounts_custom_fields, applied to the stock side of the
integration (Delivery Note / Stock Entry / Stock Ledger Entry).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Delivery Note": [
		{
			"fieldname": "journey_ref",
			"fieldtype": "Link",
			"options": "Journey",
			"label": "Journey Reference (KPC Golden Thread)",
			"insert_after": "customer",
			"read_only": 1,
			"in_standard_filter": 1,
			"in_list_view": 1,
		}
	],
	"Stock Entry": [
		{
			"fieldname": "journey_ref",
			"fieldtype": "Link",
			"options": "Journey",
			"label": "Journey Reference (KPC Golden Thread)",
			"insert_after": "stock_entry_type",
			"read_only": 1,
			"in_standard_filter": 1,
			"in_list_view": 1,
		}
	],
	"Stock Ledger Entry": [
		{
			"fieldname": "journey_ref",
			"fieldtype": "Link",
			"options": "Journey",
			"label": "Journey Reference (KPC Golden Thread)",
			"insert_after": "voucher_no",
			"read_only": 1,
			"in_standard_filter": 1,
			"in_list_view": 1,
		}
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch)
