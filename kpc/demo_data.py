# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Seed data for a complete, end-to-end demonstration of the KPC Operations
Golden Thread - one cargo, walked through all 13 steps, deliberately
routed through the AI predictive-maintenance cascade and the
variance/tolerance controls along the way so every rule built across all 5
phases has at least one real, persisted example to point to.

Run once with:

    bench --site <site> execute kpc.demo_data.create_demo_data

Safe to re-run: every record is created only if it doesn't already exist,
keyed on the demo's fixed business identifiers (vessel name, terminal
codes, etc.) rather than autoname counters. If an earlier run left an
*incomplete* journey (e.g. it predates a feature added since, or a step
failed partway), re-running create_demo_data() will not touch it - use
reset_demo_data() first:

    bench --site <site> execute kpc.demo_data.reset_demo_data

This cancels and deletes everything downstream of the demo's Oil Shipment
(which is immutable by design - see OilShipment.on_trash - so it is always
reused, never recreated) and rewinds the Journey back to Step 1, so the
next create_demo_data() rebuilds Steps 2-13 from scratch.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

COMPANY = "Kenya Pipeline Company"
CUSTOMER = "Savannah Fuels Distributors"

# Doctypes carrying journey_ref directly, in the order they must be
# *cancelled* (most-downstream/last-created first) before they can be
# deleted. Financial Posting isn't submittable, so it's just deleted.
_SUBMITTABLE_DOWNSTREAM_DOCTYPES = [
	"Invoice",
	"Dispatch",
	"Allocation",
	"Reconciliation",
	"Maintenance Work Order",
	"Terminal Receipt",
	"Pipeline Batch",
	"Nomination",
	"Tank Measurement",
]
_NON_SUBMITTABLE_DOWNSTREAM_DOCTYPES = [
	"Financial Posting",
	"Variance",
	"AI Recommendation",
	"AI Prediction",
	"AI Alert",
	"Movement",
	"Quality Result",
	"Inventory Position",
]


def _journey_is_fully_built(journey_ref: str) -> bool:
	"""'Complete' means more than reaching Step 13 - a journey built by an
	older version of this script can be at Step 13 while still missing a
	feature added since (e.g. Dispatch.delivery_note, added when the
	ERPNext Stock integration was introduced). Check for that explicitly
	rather than trusting current_step alone."""
	if frappe.db.get_value("Journey", journey_ref, "current_step") != "13. Financial Posting":
		return False

	dispatches = frappe.get_all("Dispatch", filters={"journey_ref": journey_ref}, pluck="delivery_note")
	return bool(dispatches) and all(dispatches)


def create_demo_data():
	frappe.set_user("Administrator")

	terminals = _create_terminals()
	product = _create_product()
	tanks = _create_tanks(terminals, product)
	customer = _create_customer()
	tariff = _create_tariff(terminals, product)

	journey_ref = _run_golden_thread(terminals, product, tanks, customer, tariff)

	frappe.db.commit()
	_print_summary(journey_ref)
	return journey_ref


def reset_demo_data(vessel_name: str = "MT African Pride"):
	"""Cancel and delete everything downstream of the demo Oil Shipment so
	create_demo_data() can rebuild Steps 2-13 cleanly. The Oil Shipment and
	Journey themselves are kept (Oil Shipment cannot be deleted by design);
	the Journey's audit log is rewound to just its Step 1 entry."""
	frappe.set_user("Administrator")

	journey_ref = frappe.db.get_value("Oil Shipment", {"vessel_name": vessel_name}, "journey_ref")
	if not journey_ref:
		print(f"No demo journey found for vessel '{vessel_name}' - nothing to reset.")
		return

	journey = frappe.get_doc("Journey", journey_ref)
	if _journey_is_fully_built(journey_ref):
		print(f"Journey {journey_ref} is already complete - nothing to reset.")
		return

	capacity_assessment = frappe.db.get_value(
		"Pipeline Batch", {"journey_ref": journey_ref}, "capacity_assessment"
	)

	for doctype in _SUBMITTABLE_DOWNSTREAM_DOCTYPES:
		for name in frappe.get_all(doctype, filters={"journey_ref": journey_ref}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

	for doctype in _NON_SUBMITTABLE_DOWNSTREAM_DOCTYPES:
		for name in frappe.get_all(doctype, filters={"journey_ref": journey_ref}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

	if capacity_assessment:
		frappe.delete_doc("Capacity Assessment", capacity_assessment, ignore_permissions=True, force=True)

	journey.reload()
	journey.journey_log = [row for row in journey.journey_log if row.reference_doctype == "Oil Shipment"]
	journey.current_step = "1. Shipment"
	journey.save(ignore_permissions=True)

	frappe.db.commit()
	print(f"Reset {journey_ref} back to Step 1. Run create_demo_data() to rebuild Steps 2-13.")


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------


def _create_terminals():
	defs = {
		"MSA-01": {
			"terminal_name": "Mombasa Terminal",
			"terminal_type": "Discharge",
			"location": "Mombasa, Kenya",
			"company": COMPANY,
		},
		"NBO-01": {
			"terminal_name": "Nairobi Terminal (Embakasi)",
			"terminal_type": "Loading",
			"location": "Nairobi, Kenya",
			"company": COMPANY,
		},
	}
	terminals = {}
	for code, fields in defs.items():
		if not frappe.db.exists("Terminal", code):
			frappe.get_doc({"doctype": "Terminal", "terminal_code": code, **fields}).insert()
		terminals[code] = code
	return terminals


def _create_product():
	item_code = "AGO-DIESEL"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": "Automotive Gas Oil (Diesel)",
				"item_group": "Products",
				"stock_uom": "Kilolitre",
				"density_at_15c": 0.8300,
				"reference_temperature_c": 15,
				"is_petroleum_product": 1,
				"standard_rate": 120,
			}
		).insert()
	return item_code


def _create_tanks(terminals, product):
	defs = {
		"TK-101": {
			"tank_name": "Mombasa Tank 101",
			"terminal": terminals["MSA-01"],
			"capacity_kl": 10000,
			"reference_height_mm": 15000,
		},
		"TK-201": {
			"tank_name": "Nairobi Tank 201",
			"terminal": terminals["NBO-01"],
			"capacity_kl": 8000,
			"reference_height_mm": 12000,
		},
	}
	tanks = {}
	for code, fields in defs.items():
		if not frappe.db.exists("Oil Tank", code):
			frappe.get_doc(
				{
					"doctype": "Oil Tank",
					"tank_code": code,
					"product": product,
					"current_state": "Active",
					"safe_fill_capacity_kl": fields["capacity_kl"] * 0.95,
					"dead_stock_kl": fields["capacity_kl"] * 0.02,
					**fields,
				}
			).insert()
		elif not frappe.db.get_value("Oil Tank", code, "warehouse"):
			# Tank predates the Warehouse-provisioning feature - before_insert
			# only fires on creation, so backfill it explicitly here.
			from kpc.petroleum_operations.integrations.stock import get_or_create_tank_warehouse

			tank = frappe.get_doc("Oil Tank", code)
			tank.db_set("warehouse", get_or_create_tank_warehouse(tank), update_modified=False)
		tanks[code] = code
	return tanks


def _create_customer():
	if not frappe.db.exists("Customer", CUSTOMER):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": CUSTOMER,
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}
		).insert()
	return CUSTOMER


def _create_tariff(terminals, product):
	"""Created here, alongside the other masters, rather than at Invoice
	time - a Tariff is a rate card that exists ahead of any specific
	delivery, not something decided per-invoice. This also means Dispatch
	(Step 11) can bill Delivery Notes at the real commercial rate instead
	of a rough Item reference price - see integrations.stock.resolve_delivery_rate."""
	filters = {
		"product": product,
		"origin_terminal": terminals["MSA-01"],
		"destination_terminal": terminals["NBO-01"],
	}
	name = frappe.db.get_value("Tariff", filters)
	if name:
		return name

	tariff = frappe.get_doc({"doctype": "Tariff", "rate_per_kl": 3500, "currency": "KES", **filters}).insert()
	return tariff.name


# ---------------------------------------------------------------------------
# The Golden Thread - one journey, all 13 steps
# ---------------------------------------------------------------------------


def _run_golden_thread(terminals, product, tanks, customer, tariff) -> str:
	"""Steps 2-13 below assume nothing downstream of the Oil Shipment exists
	yet - true on a first run, and true again after reset_demo_data() has
	cancelled/deleted everything downstream of an incomplete journey (Oil
	Shipment itself is immutable by design - see OilShipment.on_trash - so
	a reset can never delete it; it can only be reused)."""
	vessel_name = "MT African Pride"
	existing = frappe.db.get_value(
		"Oil Shipment", {"vessel_name": vessel_name}, ["name", "journey_ref"], as_dict=True
	)

	if existing:
		if _journey_is_fully_built(existing.journey_ref):
			return existing.journey_ref
		shipment = frappe.get_doc("Oil Shipment", existing.name)
		journey_ref = existing.journey_ref
	else:
		# Step 1: Shipment
		shipment = frappe.get_doc(
			{
				"doctype": "Oil Shipment",
				"vessel_name": vessel_name,
				"vessel_imo_number": "IMO9876543",
				"bill_of_lading_no": "BL-KPC-2026-0417",
				"product": product,
				"terminal": terminals["MSA-01"],
				"planned_quantity_kl": 5000,
				"eta": now_datetime(),
			}
		).insert()
		journey_ref = shipment.journey_ref

		for state in ("Vessel Arrived", "Discharging", "Received"):
			shipment.reload()
			shipment.workflow_state = state
			shipment.save()

	# Step 2: Receipt (Tank Measurement)
	tank_measurement = frappe.get_doc(
		{
			"doctype": "Tank Measurement",
			"journey_ref": journey_ref,
			"shipment": shipment.name,
			"tank": tanks["TK-101"],
			"measurement_type": "Closing",
			"observed_level_mm": 6000,
			"observed_temperature_c": 28,
			"density_at_15c": 0.8300,
		}
	).insert()
	tank_measurement.submit()

	# Step 3: Quality Result - Accepted
	quality_result = frappe.get_doc(
		{
			"doctype": "Quality Result",
			"journey_ref": journey_ref,
			"shipment": shipment.name,
			"tank": tanks["TK-101"],
			"product": product,
			"lab_reference_no": "LAB-2026-0417",
			"parameters": [
				{
					"parameter": "Density @ 15C",
					"specification_min": 0.82,
					"specification_max": 0.845,
					"result_value": 0.83,
					"uom": "kg/L",
				},
				{
					"parameter": "Water Content",
					"specification_min": 0,
					"specification_max": 0.05,
					"result_value": 0.01,
					"uom": "% vol",
				},
				{
					"parameter": "Flash Point",
					"specification_min": 55,
					"specification_max": 0,
					"result_value": 62,
					"uom": "C",
				},
			],
		}
	).insert()
	quality_result.workflow_state = "Accepted"
	quality_result.save()

	# Step 4: Inventory Position (origin receipt)
	frappe.get_doc(
		{
			"doctype": "Inventory Position",
			"journey_ref": journey_ref,
			"tank": tanks["TK-101"],
			"position_date": today(),
			"opening_volume_kl": 0,
			"receipts_kl": tank_measurement.net_standard_volume_kl,
		}
	).insert()

	# Step 5: Nomination
	nomination = frappe.get_doc(
		{
			"doctype": "Nomination",
			"journey_ref": journey_ref,
			"customer": customer,
			"company": COMPANY,
			"origin_terminal": terminals["MSA-01"],
			"destination_terminal": terminals["NBO-01"],
			"nominated_quantity_kl": 2000,
			"requested_delivery_date": add_days(today(), 3),
		}
	).insert()
	nomination.submit()

	# Step 6: Capacity Assessment + Pipeline Batch
	capacity = frappe.get_doc(
		{
			"doctype": "Capacity Assessment",
			"origin_terminal": terminals["MSA-01"],
			"destination_terminal": terminals["NBO-01"],
			"period_start": today(),
			"period_end": add_days(today(), 6),
			"pipeline_capacity_kl_per_day": 1000,
		}
	).insert()

	pipeline_batch = frappe.get_doc(
		{
			"doctype": "Pipeline Batch",
			"nomination": nomination.name,
			"batch_sequence_no": 1,
			"planned_volume_kl": 2000,
			"capacity_assessment": capacity.name,
			"scheduled_start": now_datetime(),
			"scheduled_end": add_to_date(now_datetime(), hours=8),
		}
	).insert()
	pipeline_batch.submit()

	# Step 7: Movement - deliberately breached telemetry, to demonstrate the
	# full AI Alert -> Prediction -> Recommendation -> Approval -> Work Order
	# cascade with real, persisted records.
	movement = frappe.get_doc(
		{
			"doctype": "Movement",
			"pipeline_batch": pipeline_batch.name,
			"pipeline_route": "Mombasa-Nairobi (Line 1)",
			"movement_status": "In Transit",
			"start_datetime": now_datetime(),
			"monitored_pressure_bar": 60,  # over the 15-45 bar normal range
			"monitored_flow_rate_m3h": 500,
			"monitored_vibration_mm_s": 10.0,  # over the 7.1 mm/s alarm threshold
		}
	).insert()

	ai_recommendation_name = frappe.get_all(
		"AI Recommendation", filters={"movement": movement.name}, pluck="name"
	)[0]
	ai_recommendation = frappe.get_doc("AI Recommendation", ai_recommendation_name)
	ai_recommendation.details = (
		"Vibration and pressure both elevated on Line 1 pump station KP2 - dispatched inspection team."
	)
	ai_recommendation.workflow_state = "Approved"
	ai_recommendation.save()

	work_order = frappe.get_doc(
		{
			"doctype": "Maintenance Work Order",
			"ai_recommendation": ai_recommendation.name,
			"journey_ref": journey_ref,
			"work_order_type": "Corrective Maintenance",
			"description": "Inspect and calibrate Line 1 pump station KP2 following pressure/vibration alert.",
			"scheduled_date": add_days(today(), 1),
			"execution_status": "Completed",
			"completion_notes": "Pump seal replaced; vibration back within normal range on re-test.",
		}
	).insert()
	work_order.submit()

	movement.reload()
	movement.movement_status = "Completed"
	movement.end_datetime = now_datetime()
	movement.save()

	# Step 8: Terminal Receipt
	terminal_receipt = frappe.get_doc(
		{
			"doctype": "Terminal Receipt",
			"movement": movement.name,
			"destination_tank": tanks["TK-201"],
			"observed_level_mm": 3000,
			"observed_temperature_c": 26,
			"density_at_15c": 0.8300,
		}
	).insert()
	terminal_receipt.submit()

	# Step 9: Reconciliation - deliberately over the default 0.5% tolerance,
	# to demonstrate the justification gate, then Variance classification
	# and approval.
	reconciliation = frappe.get_doc(
		{"doctype": "Reconciliation", "terminal_receipt": terminal_receipt.name}
	).insert()
	reconciliation.justification = (
		f"Variance of {reconciliation.variance_percent}% is within expected VCF temperature "
		"correction for an 11C swing between origin and destination gauging; no physical loss "
		"indicators observed. Approved for acceptance by Finance."
	)
	reconciliation.save()
	reconciliation.submit()

	variance = frappe.get_doc(
		{
			"doctype": "Variance",
			"reconciliation": reconciliation.name,
			"loss_category": "Temperature Variation",
			"classification_notes": "Consistent with VCF correction; no corrective action required.",
		}
	).insert()
	variance.workflow_state = "Approved"
	variance.save()

	# Step 10: Allocation
	allocation = frappe.get_doc(
		{
			"doctype": "Allocation",
			"nomination": nomination.name,
			"reconciliation": reconciliation.name,
			"allocated_quantity_kl": reconciliation.received_quantity_kl,
		}
	).insert()
	allocation.submit()

	# Step 11: Dispatch - two consignments, to show a multi-line Invoice later
	dispatch_1 = frappe.get_doc(
		{
			"doctype": "Dispatch",
			"allocation": allocation.name,
			"destination_tank": tanks["TK-201"],
			"dispatch_mode": "Truck",
			"dispatched_quantity_kl": 1200,
			"vehicle_or_vessel_ref": "KDA 214C",
			"driver_or_agent": "J. Mwangi",
		}
	).insert()
	dispatch_1.submit()

	dispatch_2 = frappe.get_doc(
		{
			"doctype": "Dispatch",
			"allocation": allocation.name,
			"destination_tank": tanks["TK-201"],
			"dispatch_mode": "Truck",
			"dispatched_quantity_kl": 700,
			"vehicle_or_vessel_ref": "KDB 552F",
			"driver_or_agent": "S. Otieno",
		}
	).insert()
	dispatch_2.submit()

	# Step 12: Invoice (Tariff was already created as a master, above - see
	# _create_tariff) -> rated lines -> real Sales Invoice on submit
	invoice = frappe.get_doc(
		{
			"doctype": "Invoice",
			"journey_ref": journey_ref,
			"customer": customer,
			"company": COMPANY,
			"lines": [
				{"dispatch": dispatch_1.name, "tariff": tariff},
				{"dispatch": dispatch_2.name, "tariff": tariff},
			],
		}
	).insert()
	invoice.submit()

	# Step 13: Financial Posting is created automatically by Invoice.on_submit.

	return journey_ref


def _print_summary(journey_ref: str):
	journey = frappe.get_doc("Journey", journey_ref)
	print("\n" + "=" * 72)
	print("KPC OPERATIONS - DEMO DATA SEEDED")
	print("=" * 72)
	print(f"Golden Thread: {journey_ref}  (status={journey.status}, step={journey.current_step})")
	print(f"Audit trail: {len(journey.journey_log)} entries")
	print("-" * 72)
	for row in journey.journey_log:
		print(f"  {row.step:<26} {row.reference_doctype:<22} {row.reference_name}")

	print("-" * 72)
	print("ERPNext Stock & Accounts (created alongside the KPC records above):")
	tank_names = ("TK-101", "TK-201")
	warehouses = frappe.get_all("Warehouse", filters={"warehouse_name": ["in", tank_names]}, pluck="name")
	for name in warehouses:
		qty = frappe.db.get_value("Bin", {"warehouse": name, "item_code": "AGO-DIESEL"}, "actual_qty") or 0
		print(f"  Warehouse            {name:<22} {qty} KL on hand")

	stock_entries = frappe.get_all(
		"Stock Entry",
		filters={"journey_ref": journey_ref},
		fields=["name", "stock_entry_type"],
		order_by="creation",
	)
	for row in stock_entries:
		print(f"  Stock Entry          {row.stock_entry_type:<22} {row.name}")
	for row in frappe.get_all(
		"Delivery Note", filters={"journey_ref": journey_ref}, fields=["name", "grand_total"], order_by="creation"
	):
		print(f"  Delivery Note        {row.name:<22} KES {row.grand_total:,.2f}")
	invoice = frappe.db.get_value("Invoice", {"journey_ref": journey_ref}, "sales_invoice")
	if invoice:
		si = frappe.db.get_value("Sales Invoice", invoice, "grand_total")
		print(f"  Sales Invoice        {invoice:<22} KES {si:,.2f}")

	print("=" * 72)
	print(f"Open the KPC workspace in Desk, or go straight to /app/journey/{journey_ref}")
	print("=" * 72 + "\n")
