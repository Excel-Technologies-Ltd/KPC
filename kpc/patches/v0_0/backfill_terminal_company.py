# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Terminal.company is new (added to support Warehouse provisioning for
the ERPNext Stock integration) - backfill it on any Terminal created
before the field existed, using the site's single default Company. Runs
post_model_sync (after the new column is synced into the DB).
"""

import frappe


def execute():
	default_company = frappe.defaults.get_global_default("company")
	if not default_company:
		return

	for name in frappe.get_all("Terminal", filters={"company": ["in", ("", None)]}, pluck="name"):
		frappe.db.set_value("Terminal", name, "company", default_company)
