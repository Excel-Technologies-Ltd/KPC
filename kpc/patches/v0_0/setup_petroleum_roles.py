# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Create the RBAC roles used across the whole KPC Operations platform.

Defined once, up front, in Phase 1 so every later phase can attach
permissions to an existing role rather than growing a second source of
truth for "who is allowed to do what".
"""

import frappe

ROLES = [
	"Terminal Operator",
	"Quality Analyst",
	"Quality Manager",
	"Scheduler & Operations Controller",
	"Commercial Officer",
	"Maintenance Manager",
	"Finance Officer",
]


def execute():
	for role_name in ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
