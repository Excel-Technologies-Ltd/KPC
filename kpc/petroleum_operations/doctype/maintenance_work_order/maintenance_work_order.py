# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kpc.petroleum_operations.utils import log_journey_step


class MaintenanceWorkOrder(Document):
	def validate(self):
		self.validate_recommendation_approved()

	def validate_recommendation_approved(self):
		if not self.ai_recommendation:
			return
		state = frappe.db.get_value("AI Recommendation", self.ai_recommendation, "workflow_state")
		if state != "Approved":
			frappe.throw(
				_("AI Recommendation {0} must be Approved before a Work Order can be raised from it.").format(
					self.ai_recommendation
				)
			)

	def on_submit(self):
		log_journey_step(self.journey_ref, "7. Movement", self)
