# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from kpc.petroleum_operations.utils import derive_failure_risk, log_journey_step, suggest_action


class AIPrediction(Document):
	def validate(self):
		result = derive_failure_risk(self.anomaly_score)
		self.failure_risk_percent = result["failure_risk_percent"]
		self.risk_horizon = result["risk_horizon"]
		if self.ai_alert:
			self.basis = frappe.db.get_value("AI Alert", self.ai_alert, "description")

	def after_insert(self):
		log_journey_step(self.journey_ref, "7. Movement", self)
		self.create_recommendation()

	def create_recommendation(self):
		"""Draft-only: a suggested intervention, not an approved one. The
		Maintenance Manager role is the exclusive approver (see the
		AI Recommendation Workflow) - this only proposes."""
		parameters, severity = [], "Medium"
		if self.ai_alert:
			alert = frappe.db.get_value(
				"AI Alert", self.ai_alert, ["parameter_breached", "severity"], as_dict=True
			)
			parameters = [p.strip() for p in (alert.parameter_breached or "").split(",") if p.strip()]
			severity = alert.severity or severity

		frappe.get_doc(
			{
				"doctype": "AI Recommendation",
				"journey_ref": self.journey_ref,
				"movement": self.movement,
				"ai_prediction": self.name,
				"recommended_action": suggest_action(parameters),
				"priority": severity,
			}
		).insert(ignore_permissions=True)
