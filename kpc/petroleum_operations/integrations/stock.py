# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Integration with standard ERPNext Stock.

Same philosophy as integrations.accounts: this module never edits a Stock
Ledger Entry itself. It maps each Oil Tank to a dedicated ERPNext Warehouse
and posts standard Stock Entries / a standard Delivery Note at the exact
points physical custody actually changes hands in the Golden Thread -

- Tank Measurement (Receipt from vessel)  -> Material Receipt
- Terminal Receipt (arrival at destination) -> Material Transfer
- Reconciliation (recognised transit loss)  -> Material Issue
- Dispatch (delivery to customer)           -> a real Delivery Note

- and lets ERPNext's own Stock Ledger do everything it already does well
(valuation, Bin quantities, Delivery Note -> Sales Invoice billing) instead
of a second, parallel accounting of the same physical stock.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, today

TANK_WAREHOUSE_GROUP = "Petroleum Tanks"


def get_or_create_tank_warehouse(oil_tank) -> str:
	"""Ensure a dedicated Warehouse exists for this Oil Tank (1:1) and
	return its name. Called from Oil Tank.validate() on insert."""
	if oil_tank.warehouse:
		return oil_tank.warehouse

	company = frappe.db.get_value("Terminal", oil_tank.terminal, "company")
	if not company:
		frappe.throw(
			_("Terminal {0} has no Company set - required to provision a Warehouse.").format(oil_tank.terminal)
		)

	group = _get_or_create_warehouse_group(company)

	warehouse_name = f"{oil_tank.tank_code} - {frappe.db.get_value('Company', company, 'abbr')}"
	if not frappe.db.exists("Warehouse", warehouse_name):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": oil_tank.tank_code,
				"company": company,
				"parent_warehouse": group,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	return warehouse_name


def _get_or_create_warehouse_group(company: str) -> str:
	abbr = frappe.db.get_value("Company", company, "abbr")
	group_name = f"{TANK_WAREHOUSE_GROUP} - {abbr}"
	if not frappe.db.exists("Warehouse", group_name):
		root = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ""})
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": TANK_WAREHOUSE_GROUP,
				"company": company,
				"is_group": 1,
				"parent_warehouse": root,
			}
		).insert(ignore_permissions=True)
	return group_name


def resolve_origin_tank(journey_ref: str) -> str:
	"""The Tank Measurement (Step 2) is where a journey's product first
	enters a specific Oil Tank - that tank is the 'origin' every later
	stock movement (Terminal Receipt, Reconciliation) transfers out of."""
	tank = frappe.db.get_value("Tank Measurement", {"journey_ref": journey_ref}, "tank")
	if not tank:
		frappe.throw(
			_("No Tank Measurement found for Journey {0}; cannot resolve the origin tank.").format(journey_ref)
		)
	return tank


def post_material_receipt(
	warehouse: str, item_code: str, qty: float, journey_ref: str, rate: float | None = None
):
	"""Stock Entry: product entering the Golden Thread for the first time
	(vessel -> origin tank), at Tank Measurement."""
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"purpose": "Material Receipt",
			"company": frappe.db.get_value("Warehouse", warehouse, "company"),
			"posting_date": today(),
			"journey_ref": journey_ref,
			"items": [
				{
					"item_code": item_code,
					"qty": flt(qty),
					"uom": "Kilolitre",
					"conversion_factor": 1,
					"t_warehouse": warehouse,
					"basic_rate": flt(rate) or None,
				}
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry


def post_material_transfer(
	source_warehouse: str, target_warehouse: str, item_code: str, qty: float, journey_ref: str
):
	"""Stock Entry: product moving tank-to-tank through the pipeline, at
	Terminal Receipt."""
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Transfer",
			"purpose": "Material Transfer",
			"company": frappe.db.get_value("Warehouse", source_warehouse, "company"),
			"posting_date": today(),
			"journey_ref": journey_ref,
			"items": [
				{
					"item_code": item_code,
					"qty": flt(qty),
					"uom": "Kilolitre",
					"conversion_factor": 1,
					"s_warehouse": source_warehouse,
					"t_warehouse": target_warehouse,
				}
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry


def post_material_issue(warehouse: str, item_code: str, qty: float, journey_ref: str):
	"""Stock Entry: recognised transit loss, at Reconciliation - only
	called when a Reconciliation's variance_kl is positive (product
	dispatched but never arrived)."""
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"purpose": "Material Issue",
			"company": frappe.db.get_value("Warehouse", warehouse, "company"),
			"posting_date": today(),
			"journey_ref": journey_ref,
			"items": [
				{
					"item_code": item_code,
					"qty": flt(qty),
					"uom": "Kilolitre",
					"conversion_factor": 1,
					"s_warehouse": warehouse,
				}
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry


def create_and_submit_delivery_note(dispatch) -> frappe.model.document.Document:
	"""Build and submit a standard Delivery Note for a Dispatch - this *is*
	the customer-facing delivery document (a 'delivery chalan'), and it's
	what posts the actual Stock Ledger Entry reducing the destination
	tank's Warehouse. Kept separate from Invoice/Sales Invoice: Dispatch
	(Step 11) happens before Invoice (Step 12), exactly like real delivery
	precedes billing.
	"""
	product = frappe.db.get_value("Oil Tank", dispatch.destination_tank, "product")
	warehouse = frappe.db.get_value("Oil Tank", dispatch.destination_tank, "warehouse")
	nomination = frappe.get_doc(
		"Nomination", frappe.db.get_value("Allocation", dispatch.allocation, "nomination")
	)

	delivery_note = frappe.get_doc(
		{
			"doctype": "Delivery Note",
			"customer": dispatch.customer,
			"company": nomination.company,
			"posting_date": dispatch.dispatch_datetime,
			"journey_ref": dispatch.journey_ref,
			"items": [
				{
					"item_code": product,
					"qty": flt(dispatch.dispatched_quantity_kl),
					"uom": "Kilolitre",
					"conversion_factor": 1,
					"warehouse": warehouse,
					"rate": resolve_delivery_rate(product, nomination.origin_terminal, nomination.destination_terminal),
				}
			],
		}
	)
	delivery_note.insert()
	delivery_note.submit()
	return delivery_note


def resolve_delivery_rate(product: str, origin_terminal: str, destination_terminal: str) -> float:
	"""The commercial Tariff (Step 12/Invoice's actual billing rate) if one
	is already on file for this route, else the Item's reference rate.

	Getting this right matters beyond cosmetics: ERPNext's Sales Invoice
	blocks billing a Delivery Note line for meaningfully more than that
	line's own amount (over-billing protection). If the two rates are
	wildly different - a raw reference rate vs. a real commercial tariff
	can easily be off by 10-30x for a bulk commodity - Invoice submission
	fails downstream with a confusing "Cannot overbill" error. Tariffs are
	rate cards that normally exist before a delivery happens, not decided
	per-invoice, so preferring one here reflects how this actually runs in
	practice, not just papering over the ERPNext check.
	"""
	tariff_rate = frappe.db.get_value(
		"Tariff",
		{
			"product": product,
			"origin_terminal": origin_terminal,
			"destination_terminal": destination_terminal,
			"is_active": 1,
		},
		"rate_per_kl",
	)
	if tariff_rate:
		return flt(tariff_rate)

	return flt(frappe.db.get_value("Item", product, "standard_rate"))


def propagate_journey_ref_to_stock_ledger(doc, method=None):
	"""doc_events hook: Stock Entry / Delivery Note on_submit.

	Mirrors integrations.accounts.propagate_journey_ref_to_gl_entries: runs
	after ERPNext has already created the Stock Ledger Entries, purely to
	stamp journey_ref onto rows that already exist.
	"""
	journey_ref = doc.get("journey_ref")
	if not journey_ref:
		return

	frappe.db.set_value(
		"Stock Ledger Entry", {"voucher_type": doc.doctype, "voucher_no": doc.name}, "journey_ref", journey_ref
	)
