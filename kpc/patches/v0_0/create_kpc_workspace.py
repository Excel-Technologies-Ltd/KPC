# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Create the KPC Workspace: shortcuts to the most-used entry points, plus
one card per phase of the 13-step Golden Thread, so the whole build is
navigable from a single place rather than requiring users to know every
doctype name up front.
"""

import json

import frappe

WORKSPACE_NAME = "KPC"

SHORTCUTS = [
	("Journey", "DocType", "octicon octicon-link"),
	("Oil Shipment", "DocType", None),
	("Nomination", "DocType", None),
	("Movement", "DocType", None),
	("AI Alert", "DocType", None),
	("Reconciliation", "DocType", None),
	("Invoice", "DocType", None),
	("Financial Posting", "DocType", None),
]

# (card_label, [doctype, ...])
CARDS = [
	("Golden Thread", ["Journey"]),
	(
		"Phase 1 - Inbound Logistics & Storage",
		["Terminal", "Oil Tank", "Oil Shipment", "Tank Measurement", "Quality Result", "Inventory Position"],
	),
	("Phase 2 - Commercial Planning", ["Nomination", "Capacity Assessment", "Pipeline Batch"]),
	(
		"Phase 3 - Pipeline Operations & AI",
		[
			"Movement",
			"AI Alert",
			"AI Prediction",
			"AI Recommendation",
			"Maintenance Work Order",
			"Terminal Receipt",
		],
	),
	("Phase 4 - Reconciliation & Outbound", ["Reconciliation", "Variance", "Allocation", "Dispatch"]),
	("Phase 5 - Billing & Financials", ["Tariff", "Invoice", "Financial Posting"]),
]


def execute():
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	workspace = frappe.new_doc("Workspace")
	workspace.name = WORKSPACE_NAME
	workspace.title = WORKSPACE_NAME
	workspace.label = WORKSPACE_NAME
	workspace.module = "Petroleum Operations"
	workspace.icon = "stock"
	workspace.public = 1
	workspace.is_hidden = 0
	workspace.sequence_id = 1

	for label, shortcut_type, icon in SHORTCUTS:
		row = workspace.append("shortcuts", {"label": label, "type": shortcut_type, "link_to": label})
		if icon:
			row.icon = icon

	for card_label, doctypes in CARDS:
		workspace.append("links", {"type": "Card Break", "label": card_label})
		for dt in doctypes:
			workspace.append(
				"links", {"type": "Link", "link_type": "DocType", "link_to": dt, "label": dt, "onboard": 1}
			)

	content = [_header_block("kpc-header-quick-access", "Quick Access")]
	for label, _shortcut_type, _icon in SHORTCUTS:
		content.append(
			{"id": f"kpc-shortcut-{_slug(label)}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}}
		)

	content.append({"id": "kpc-spacer-1", "type": "spacer", "data": {"col": 12}})
	content.append(_header_block("kpc-header-thread", "The 13-Step Golden Thread"))
	for card_label, _doctypes in CARDS:
		content.append(
			{"id": f"kpc-card-{_slug(card_label)}", "type": "card", "data": {"card_name": card_label, "col": 4}}
		)

	workspace.content = json.dumps(content)
	workspace.insert(ignore_permissions=True)


def _header_block(block_id: str, text: str) -> dict:
	html = f"<span class='h4'><b>{text}</b></span>"
	return {"id": block_id, "type": "header", "data": {"text": html, "col": 12}}


def _slug(text: str) -> str:
	return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")
