# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from kpc.petroleum_operations.utils import log_journey_step


class Variance(Document):
	def validate(self):
		self.validate_reconciliation_accepted()
		if self.has_value_changed("workflow_state") and self.workflow_state in ("Approved", "Rejected"):
			self.approved_by = frappe.session.user
			self.approved_on = now_datetime()

	def validate_reconciliation_accepted(self):
		if frappe.db.get_value("Reconciliation", self.reconciliation, "docstatus") != 1:
			frappe.throw(
				_("Reconciliation {0} must be accepted before its variance can be classified.").format(
					self.reconciliation
				)
			)

	def on_update(self):
		if self.has_value_changed("workflow_state"):
			log_journey_step(self.journey_ref, "9. Reconciliation", self)
