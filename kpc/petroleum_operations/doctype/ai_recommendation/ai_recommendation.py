# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from kpc.petroleum_operations.utils import log_journey_step


class AIRecommendation(Document):
	def validate(self):
		if self.has_value_changed("workflow_state") and self.workflow_state in ("Approved", "Rejected"):
			self.approved_by = frappe.session.user
			self.approved_on = now_datetime()

	def on_update(self):
		if self.has_value_changed("workflow_state"):
			log_journey_step(self.journey_ref, "7. Movement", self)
