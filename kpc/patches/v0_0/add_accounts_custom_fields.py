# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Extend standard ERPNext Accounts doctypes for the Golden Thread, and add
the Kilolitre UOM every petroleum Product/Invoice line relies on.

- Sales Invoice.journey_ref: set when the Invoice (Step 12) creates it.
- GL Entry.journey_ref: stamped by the Sales Invoice on_submit/on_cancel
  doc_events in kpc.petroleum_operations.integrations.accounts, so every
  GL posting this app causes is traceable back to a single journey without
  reading through the Sales Invoice at all.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Sales Invoice": [
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
	"GL Entry": [
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
	create_kilolitre_uom()


def create_kilolitre_uom():
	if frappe.db.exists("UOM", "Kilolitre"):
		return
	frappe.get_doc(
		{"doctype": "UOM", "uom_name": "Kilolitre", "must_be_whole_number": 0}
	).insert(ignore_permissions=True)
