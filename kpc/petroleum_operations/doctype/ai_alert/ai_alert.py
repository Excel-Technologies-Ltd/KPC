# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from kpc.petroleum_operations.utils import log_journey_step


class AIAlert(Document):
	def after_insert(self):
		log_journey_step(self.journey_ref, "7. Movement", self)
		self.create_prediction()

	def create_prediction(self):
		"""Every AI Alert produces exactly one downstream AI Prediction - the
		forecast of what happens if the anomaly isn't addressed. Kept as a
		separate doctype (rather than fields on the Alert) because a
		Prediction can later be superseded by a fresh one without losing the
		original detection event."""
		frappe.get_doc(
			{
				"doctype": "AI Prediction",
				"journey_ref": self.journey_ref,
				"movement": self.movement,
				"ai_alert": self.name,
				"anomaly_score": self.anomaly_score,
			}
		).insert(ignore_permissions=True)
