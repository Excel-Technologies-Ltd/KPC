# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Shared helpers for the Petroleum Operations module.

This module centralises logic that must behave identically across every
transaction doctype in the 13-step KPC workflow:

- Golden Thread (``journey_ref``) propagation and audit logging.
- Oil Tank operational-state guarding (Maintenance / Quarantine).
- Volumetric conversion (temperature/density correction to 15C).

Keeping this logic in one place is what lets us claim "100% auditability":
every doctype that touches the Golden Thread calls :func:`log_journey_step`
instead of re-implementing its own bookkeeping.
"""

from __future__ import annotations

import math

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

# Tank operational states that must block any transaction which would move
# product into/out of the tank (receipts, dispatches, position updates).
BLOCKING_TANK_STATES = ("Maintenance", "Quarantine", "Decommissioned")

# The 13 canonical steps of the KPC Golden Thread, in order. Stored on
# Journey.current_step and used to validate that steps are not skipped
# backwards silently (a later step is always allowed to move the pointer
# forward; it is never moved backwards automatically).
JOURNEY_STEPS = [
	"1. Shipment",
	"2. Receipt",
	"3. Quality Result",
	"4. Inventory Position",
	"5. Nomination",
	"6. Batch",
	"7. Movement",
	"8. Terminal Receipt",
	"9. Reconciliation",
	"10. Allocation",
	"11. Dispatch",
	"12. Invoice",
	"13. Financial Posting",
]


def assert_tank_available(tank: str, action: str = "record this transaction against") -> None:
	"""Raise if ``tank`` is not in a state that permits stock movement.

	Every doctype that posts volume against an Oil Tank (Tank Measurement,
	Inventory Position, and later Terminal Receipt/Movement) must call this
	before accepting the transaction.
	"""
	if not tank:
		return

	state = frappe.db.get_value("Oil Tank", tank, "current_state")
	if state in BLOCKING_TANK_STATES:
		frappe.throw(
			_("Cannot {0}: Oil Tank {1} is currently in state {2}.").format(
				action, frappe.bold(tank), frappe.bold(state)
			),
			title=_("Tank Unavailable"),
		)


def log_journey_step(journey_ref: str, step: str, doc) -> None:
	"""Append an audit row to the Journey and advance ``current_step``.

	``step`` must be one of :data:`JOURNEY_STEPS`. This is the single choke
	point through which every transaction registers itself against the
	Golden Thread, so a Journey's ``journey_log`` table is a complete,
	ordered audit trail of every document raised against it.
	"""
	if not journey_ref:
		frappe.throw(_("A Journey Reference (journey_ref) is required for this transaction."))

	if step not in JOURNEY_STEPS:
		frappe.throw(_("Unknown Golden Thread step: {0}").format(step))

	journey = frappe.get_doc("Journey", journey_ref)

	journey.append(
		"journey_log",
		{
			"step": step,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"logged_on": now_datetime(),
			"logged_by": frappe.session.user,
		},
	)

	# Only move the pointer forward; never regress it because an earlier
	# step's document was amended/re-saved after later steps already ran.
	if JOURNEY_STEPS.index(step) >= JOURNEY_STEPS.index(journey.current_step or JOURNEY_STEPS[0]):
		journey.current_step = step

	journey.save(ignore_permissions=True)


def calculate_vcf(density_at_15c: float, observed_temperature_c: float) -> float:
	"""Return the Volume Correction Factor (VCF) to standard 15C.

	Simplified implementation of the generalised-products correction from
	API MPMS Chapter 11.1 / ASTM D1250 (Table 54B), suitable for
	operational estimates. It is NOT a substitute for a certified metrology
	table and should be replaced with vendor-certified VCF tables before
	this figure is used for fiscal custody transfer.

	``density_at_15c`` is taken in kg/L (as stored on Product/Item and Tank
	Measurement, e.g. 0.8300 for diesel) and converted to kg/m3 internally
	because the K0/K1 constants below are calibrated for that unit.
	"""
	density_kg_l = flt(density_at_15c)
	if density_kg_l <= 0:
		frappe.throw(_("Density at 15C must be a positive number to calculate VCF."))

	density_kg_m3 = density_kg_l * 1000
	k0, k1 = 346.4228, 0.4388  # Table 54B - generalised refined products
	alpha = (k0 / (density_kg_m3**2)) + (k1 / density_kg_m3)
	delta_t = flt(observed_temperature_c) - 15.0

	vcf = math.exp(-alpha * delta_t * (1 + 0.8 * alpha * delta_t))
	return flt(vcf, 6)


def calculate_standard_volume(
	tank: str,
	observed_level_mm: float,
	water_dip_mm: float,
	density_at_15c: float,
	observed_temperature_c: float,
) -> dict:
	"""Shared gauge-to-standard-volume calculation.

	Used by both Tank Measurement (Receipt, origin) and Terminal Receipt
	(destination) so the two doctypes can never drift onto different
	formulas for the same physical measurement. Returns a dict with
	``gross_observed_volume_kl``, ``volume_correction_factor`` and
	``net_standard_volume_kl``, each already rounded for display.
	"""
	tank_doc = frappe.get_doc("Oil Tank", tank)
	if not tank_doc.reference_height_mm or not tank_doc.capacity_kl:
		frappe.throw(
			_("Oil Tank {0} is missing calibration data (Reference Height / Shell Capacity).").format(tank)
		)

	net_oil_level_mm = max(flt(observed_level_mm) - flt(water_dip_mm), 0)
	gross_observed_volume_kl = flt((net_oil_level_mm / tank_doc.reference_height_mm) * tank_doc.capacity_kl, 3)

	vcf = calculate_vcf(density_at_15c, observed_temperature_c)

	return {
		"gross_observed_volume_kl": gross_observed_volume_kl,
		"volume_correction_factor": vcf,
		"net_standard_volume_kl": flt(gross_observed_volume_kl * vcf, 3),
	}


def record_inventory_movement(
	tank: str, journey_ref: str, stock_owner: str | None = None, receipts_kl: float = 0, dispatches_kl: float = 0
) -> None:
	"""Append a new Inventory Position row for ``tank``, carrying forward the
	latest known closing balance as this row's opening.

	Both Terminal Receipt (arrival) and Dispatch (departure) call this so a
	tank's stock ledger stays complete and symmetric - an arrival that is
	never posted here would silently understate the tank's balance the next
	time a departure is recorded against it.
	"""
	latest = frappe.get_all(
		"Inventory Position",
		filters={"tank": tank},
		fields=["closing_volume_kl"],
		order_by="position_date desc, creation desc",
		limit=1,
	)
	opening = flt(latest[0].closing_volume_kl) if latest else 0.0

	frappe.get_doc(
		{
			"doctype": "Inventory Position",
			"journey_ref": journey_ref,
			"tank": tank,
			"stock_owner": stock_owner,
			"position_date": frappe.utils.today(),
			"opening_volume_kl": opening,
			"receipts_kl": receipts_kl,
			"dispatches_kl": dispatches_kl,
		}
	).insert(ignore_permissions=True)


# Illustrative safe-operating envelope for the AI Predictive Maintenance
# check during Movement. In production these would come from the pipeline's
# engineering design limits (per segment/pump station) rather than a single
# global constant, and the scoring below would be replaced by a trained
# anomaly-detection model - this rule-based version exists so the Golden
# Thread's AI Alert -> AI Prediction -> AI Recommendation cascade has a real,
# deterministic, explainable signal to react to.
PRESSURE_NORMAL_RANGE_BAR = (15.0, 45.0)
FLOW_RATE_NOMINAL_M3H = 500.0
FLOW_RATE_TOLERANCE_PCT = 15.0
VIBRATION_ALARM_MM_S = 7.1  # ISO 10816 zone C/D boundary, medium machines

ANOMALY_ALERT_THRESHOLD = 50  # score at/above this raises an AI Alert


def assess_pipeline_anomaly(pressure_bar: float, flow_rate_m3h: float, vibration_mm_s: float) -> dict:
	"""Score a Movement's telemetry snapshot against the safe operating
	envelope. Returns a dict with a 0-100 ``score``, the ``severity`` band,
	which ``parameters`` breached, and a human-readable ``basis`` string
	explaining the score (kept for the AI Prediction's explainability field).

	Severity is driven by the worst single reading (so one genuinely
	dangerous excursion - e.g. a pipeline overpressure - can reach Critical
	on its own) plus a smaller bonus per additional corroborating breach
	(multiple simultaneous anomalies raise confidence something is
	systemically wrong, beyond what the worst single reading implies).
	"""
	breached = []
	individual_scores = []

	lo, hi = PRESSURE_NORMAL_RANGE_BAR
	if pressure_bar is not None and not (lo <= flt(pressure_bar) <= hi):
		deviation = min(abs(flt(pressure_bar) - lo), abs(flt(pressure_bar) - hi))
		individual_scores.append(min(deviation / (hi - lo) * 100, 100))
		breached.append("Pressure")

	if flow_rate_m3h is not None:
		deviation_pct = abs(flt(flow_rate_m3h) - FLOW_RATE_NOMINAL_M3H) / FLOW_RATE_NOMINAL_M3H * 100
		if deviation_pct > FLOW_RATE_TOLERANCE_PCT:
			individual_scores.append(min(deviation_pct, 100))
			breached.append("Flow Rate")

	if vibration_mm_s is not None and flt(vibration_mm_s) > VIBRATION_ALARM_MM_S:
		over_pct = (flt(vibration_mm_s) - VIBRATION_ALARM_MM_S) / VIBRATION_ALARM_MM_S * 100
		individual_scores.append(min(over_pct, 100))
		breached.append("Vibration")

	if individual_scores:
		corroboration_bonus = 8 * (len(individual_scores) - 1)
		score = flt(min(max(individual_scores) + corroboration_bonus, 100), 1)
	else:
		score = 0.0

	if score >= 90:
		severity = "Critical"
	elif score >= 75:
		severity = "High"
	elif score >= 50:
		severity = "Medium"
	elif score >= 25:
		severity = "Low"
	else:
		severity = "Nominal"

	if breached:
		basis = _("Breached: {0} (pressure {1} bar, flow {2} m3/h, vibration {3} mm/s).").format(
			", ".join(breached), pressure_bar, flow_rate_m3h, vibration_mm_s
		)
	else:
		basis = _("All readings within the normal operating envelope.")

	return {
		"score": score,
		"severity": severity,
		"parameters": breached,
		"basis": basis,
		"is_alertable": score >= ANOMALY_ALERT_THRESHOLD,
	}


def derive_failure_risk(anomaly_score: float) -> dict:
	"""Map an anomaly score to an illustrative failure-risk percentage and
	horizon band. A real deployment would replace this with a model trained
	on failure history; kept deterministic here so a given score always
	produces the same, explainable prediction."""
	score = flt(anomaly_score)

	if score >= 90:
		risk_percent, horizon = min(70 + (score - 90), 99), "Immediate (<24h)"
	elif score >= 75:
		risk_percent, horizon = 45 + (score - 75), "7 Days"
	elif score >= 50:
		risk_percent, horizon = 20 + (score - 50), "30 Days"
	else:
		risk_percent, horizon = max(score / 2, 5), "90 Days"

	return {"failure_risk_percent": flt(risk_percent, 1), "risk_horizon": horizon}


# Default suggested intervention per breached telemetry parameter. A real
# system would rank several candidate interventions by expected effectiveness;
# this is a first-pass mapping a Maintenance Manager can always override.
RECOMMENDED_ACTION_BY_PARAMETER = {
	"Vibration": "Vibration Sensor Calibration",
	"Pressure": "Pressure Relief Valve Check",
	"Flow Rate": "Full Pipeline Segment Inspection",
}


def suggest_action(parameters_breached: list) -> str:
	if len(parameters_breached) == 1 and parameters_breached[0] in RECOMMENDED_ACTION_BY_PARAMETER:
		return RECOMMENDED_ACTION_BY_PARAMETER[parameters_breached[0]]
	return "Full Pipeline Segment Inspection"
