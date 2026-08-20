# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt


class CapacityAssessment(Document):
	def validate(self):
		if date_diff(self.period_end, self.period_start) < 0:
			frappe.throw(_("Period End cannot be before Period Start."))
		self.recalculate_commitment()

	def recalculate_commitment(self):
		"""Sum Approved (submitted) Pipeline Batches on the same route whose
		schedule overlaps this assessment's period. Re-run automatically on
		save; callable directly (e.g. from a client "Recalculate" button) to
		pick up Pipeline Batches submitted after this record was created."""
		overlapping = frappe.get_all(
			"Pipeline Batch",
			filters={
				"origin_terminal": self.origin_terminal,
				"destination_terminal": self.destination_terminal,
				"docstatus": 1,
				"scheduled_start": ["<=", self.period_end],
				"scheduled_end": [">=", self.period_start],
			},
			fields=["planned_volume_kl"],
		)
		self.committed_kl = flt(sum(flt(row.planned_volume_kl) for row in overlapping), 3)

		period_days = max(date_diff(self.period_end, self.period_start) + 1, 1)
		total_capacity = flt(self.pipeline_capacity_kl_per_day) * period_days
		self.available_capacity_kl = flt(total_capacity - self.committed_kl, 3)

	@frappe.whitelist()
	def refresh_commitment(self):
		self.recalculate_commitment()
		self.save()
		return {
			"committed_kl": self.committed_kl,
			"available_capacity_kl": self.available_capacity_kl,
		}
