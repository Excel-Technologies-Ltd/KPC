# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Allow Invoice's commercial Tariff rate to differ from the placeholder
rate a Dispatch's Delivery Note was created with.

Physical delivery (Step 11 / Dispatch) happens before commercial billing
(Step 12 / Invoice) in the Golden Thread, so the Delivery Note this app
creates can only carry a reference rate (the Item's standard_rate) at the
time it's made - the actual Tariff rate is often decided independently.
ERPNext's default 0% over-billing allowance compares the Sales Invoice's
billed amount against the Delivery Note's amount and blocks any positive
difference; raising the allowance to 100% lets the Tariff rate always
govern billing without weakening any other control in the system (it only
affects the delivered-vs-billed *amount* check, not quantity - Invoice's
own validate_kilolitre_uom and Dispatch's remaining-balance checks still
enforce the volumes match).
"""

import frappe


def execute():
	frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", 100)
