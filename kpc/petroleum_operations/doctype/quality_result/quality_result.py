# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from kpc.petroleum_operations.utils import log_journey_step


class QualityResult(Document):
	def validate(self):
		self.evaluate_parameters()
		self.stamp_approval()

	def evaluate_parameters(self):
		if not self.parameters:
			frappe.throw(_("At least one quality parameter result is required."))

		all_within_spec = True
		for row in self.parameters:
			row.is_within_spec = self.is_row_within_spec(row)
			if not row.is_within_spec:
				all_within_spec = False

		self.overall_result = "Pass" if all_within_spec else "Fail"

	@staticmethod
	def is_row_within_spec(row) -> bool:
		if row.specification_min not in (None, 0) and row.result_value < row.specification_min:
			return False
		if row.specification_max not in (None, 0) and row.result_value > row.specification_max:
			return False
		return True

	def stamp_approval(self):
		"""Approval is a workflow transition (Pending -> Accepted/Quarantined),
		restricted to the Quality Manager role by the Workflow definition.
		This just records who/when for audit."""
		if self.has_value_changed("workflow_state") and self.workflow_state in ("Accepted", "Quarantined"):
			self.approved_by = frappe.session.user
			self.approved_on = now_datetime()

	def on_update(self):
		if self.journey_ref and self.has_value_changed("workflow_state"):
			log_journey_step(self.journey_ref, "3. Quality Result", self)

		# Quarantine feeds back to the physical asset: a Fail/Quarantined
		# result must stop further receipts into the sampled tank.
		if self.workflow_state == "Quarantined" and self.tank:
			frappe.db.set_value("Oil Tank", self.tank, "current_state", "Quarantine")
