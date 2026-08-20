# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.utils import log_journey_step


class PipelineBatch(Document):
	def validate(self):
		self.validate_schedule()
		self.validate_against_nomination()
		self.validate_against_capacity()

	def validate_schedule(self):
		if self.scheduled_start and self.scheduled_end and self.scheduled_end <= self.scheduled_start:
			frappe.throw(_("Scheduled End must be after Scheduled Start."))

	def validate_against_nomination(self):
		nomination = frappe.get_doc("Nomination", self.nomination)
		if nomination.docstatus != 1:
			frappe.throw(_("Nomination {0} must be submitted (accepted) before batching.").format(self.nomination))

		already_batched = flt(
			frappe.db.sql(
				"""
				select coalesce(sum(planned_volume_kl), 0)
				from `tabPipeline Batch`
				where nomination = %s and docstatus < 2 and name != %s
				""",
				(self.nomination, self.name or ""),
			)[0][0]
		)
		if already_batched + flt(self.planned_volume_kl) > flt(nomination.nominated_quantity_kl):
			frappe.throw(
				_("Batched volume ({0} KL) would exceed Nomination {1}'s nominated quantity ({2} KL).").format(
					already_batched + flt(self.planned_volume_kl), self.nomination, nomination.nominated_quantity_kl
				)
			)

	def validate_against_capacity(self):
		if not self.capacity_assessment:
			return
		available = flt(
			frappe.db.get_value("Capacity Assessment", self.capacity_assessment, "available_capacity_kl")
		)
		if flt(self.planned_volume_kl) > available:
			frappe.throw(
				_("Planned volume ({0} KL) exceeds available capacity ({1} KL) on {2}.").format(
					self.planned_volume_kl, available, self.capacity_assessment
				)
			)

	def on_submit(self):
		log_journey_step(self.journey_ref, "6. Batch", self)
		if self.capacity_assessment:
			frappe.get_doc("Capacity Assessment", self.capacity_assessment).refresh_commitment()

	def on_cancel(self):
		if self.capacity_assessment:
			frappe.get_doc("Capacity Assessment", self.capacity_assessment).refresh_commitment()
