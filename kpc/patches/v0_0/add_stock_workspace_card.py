# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Extend the KPC Workspace (created by create_kpc_workspace) with the
standard ERPNext doctypes the Stock/Accounts integration now touches -
Warehouse, Stock Entry, Delivery Note, Sales Invoice - plus a Delivery
Note quick-access shortcut, so the workspace stays a complete map of
everything the Golden Thread creates, not just this app's own doctypes.

Kept as its own patch (rather than editing create_kpc_workspace.py's
already-executed logic) since that patch only runs once per site; this
one carries the update to sites that installed the app before the Stock
integration existed. create_kpc_workspace.py's own CARDS/SHORTCUTS lists
are updated too, so a fresh install gets everything in one pass and this
patch becomes a no-op there.
"""

import json

import frappe

WORKSPACE_NAME = "KPC"
CARD_LABEL = "ERPNext Integration (Accounts & Stock)"
CARD_ITEMS = ["Warehouse", "Stock Entry", "Delivery Note", "Sales Invoice"]
SHORTCUT_LABEL = "Delivery Note"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	content = json.loads(workspace.content)

	if not any(link.label == CARD_LABEL for link in workspace.links):
		workspace.append("links", {"type": "Card Break", "label": CARD_LABEL})
		for dt in CARD_ITEMS:
			workspace.append("links", {"type": "Link", "link_type": "DocType", "link_to": dt, "label": dt})
		content.append(
			{"id": "kpc-card-erpnext-integration", "type": "card", "data": {"card_name": CARD_LABEL, "col": 4}}
		)

	if not any(s.label == SHORTCUT_LABEL for s in workspace.shortcuts):
		workspace.append("shortcuts", {"label": SHORTCUT_LABEL, "type": "DocType", "link_to": SHORTCUT_LABEL})
		shortcut_block = {
			"id": "kpc-shortcut-delivery-note",
			"type": "shortcut",
			"data": {"shortcut_name": SHORTCUT_LABEL, "col": 3},
		}
		spacer_index = next((i for i, b in enumerate(content) if b["id"] == "kpc-spacer-1"), len(content))
		content.insert(spacer_index, shortcut_block)

	workspace.content = json.dumps(content)
	workspace.save(ignore_permissions=True)
