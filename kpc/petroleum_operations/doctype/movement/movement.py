# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kpc.petroleum_operations.utils import assess_pipeline_anomaly, log_journey_step

VALID_TRANSITIONS = {
	"Draft": {"In Transit", "Halted"},
	"In Transit": {"Completed", "Halted"},
	"Halted": {"In Transit", "Completed"},
	"Completed": set(),
}


class Movement(Document):
	def validate(self):
		self.validate_batch_approved()
		self.validate_status_transition()
		self.evaluate_telemetry()

	def validate_batch_approved(self):
		if frappe.db.get_value("Pipeline Batch", self.pipeline_batch, "docstatus") != 1:
			frappe.throw(_("Pipeline Batch {0} must be Approved before it can be moved.").format(self.pipeline_batch))

	def validate_status_transition(self):
		if self.is_new() or not self.has_value_changed("movement_status"):
			return
		previous = frappe.db.get_value("Movement", self.name, "movement_status")
		if previous and self.movement_status not in VALID_TRANSITIONS.get(previous, set()):
			frappe.throw(
				_("Cannot move Movement status from {0} to {1}.").format(previous, self.movement_status)
			)

	def evaluate_telemetry(self):
		"""Run on every save while telemetry has been entered - this is the
		'AI Predictive Maintenance event during pipeline movement' called for
		in the brief. See kpc.petroleum_operations.utils.assess_pipeline_anomaly
		for the (rule-based, explainable) scoring itself."""
		if not any([self.monitored_pressure_bar, self.monitored_flow_rate_m3h, self.monitored_vibration_mm_s]):
			return

		result = assess_pipeline_anomaly(
			self.monitored_pressure_bar, self.monitored_flow_rate_m3h, self.monitored_vibration_mm_s
		)
		self.anomaly_score = result["score"]
		self.anomaly_severity = result["severity"]
		self._anomaly_result = result  # stashed for on_update, not persisted

	def on_update(self):
		if self.has_value_changed("movement_status"):
			log_journey_step(self.journey_ref, "7. Movement", self)
		self.raise_ai_alert_if_needed()

	def raise_ai_alert_if_needed(self):
		result = getattr(self, "_anomaly_result", None)
		if not result or not result["is_alertable"]:
			return

		# Don't spam a new Alert on every subsequent save while the same
		# breach persists - only raise while none is currently Open for this
		# Movement.
		if frappe.db.exists("AI Alert", {"movement": self.name, "status": "Open"}):
			return

		alert = frappe.get_doc(
			{
				"doctype": "AI Alert",
				"journey_ref": self.journey_ref,
				"movement": self.name,
				"anomaly_score": result["score"],
				"severity": result["severity"],
				"parameter_breached": ", ".join(result["parameters"]) or "Multiple",
				"description": result["basis"],
			}
		)
		alert.insert(ignore_permissions=True)

		# db_set (not frappe.db.set_value) keeps this in-memory document's
		# own `modified` timestamp in sync with what was just written, so a
		# caller holding this same `self` doesn't hit a false-positive
		# TimestampMismatchError on its next .save(). update_modified=False
		# because this is a system-computed side effect, not a user edit.
		self.db_set("alert_triggered", 1, update_modified=False)
