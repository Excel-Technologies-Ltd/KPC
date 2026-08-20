# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.utils import log_journey_step


class Allocation(Document):
	def validate(self):
		self.validate_reconciliation_accepted()
		self.validate_quantity()

	def validate_reconciliation_accepted(self):
		if frappe.db.get_value("Reconciliation", self.reconciliation, "docstatus") != 1:
			frappe.throw(
				_("Reconciliation {0} must be accepted before it can be allocated.").format(self.reconciliation)
			)

	def validate_quantity(self):
		received = flt(frappe.db.get_value("Reconciliation", self.reconciliation, "received_quantity_kl"))
		nominated = flt(frappe.db.get_value("Nomination", self.nomination, "nominated_quantity_kl"))

		already_allocated = flt(
			frappe.db.sql(
				"""
				select coalesce(sum(allocated_quantity_kl), 0)
				from `tabAllocation`
				where reconciliation = %s and docstatus < 2 and name != %s
				""",
				(self.reconciliation, self.name or ""),
			)[0][0]
		)

		if already_allocated + flt(self.allocated_quantity_kl) > received:
			frappe.throw(
				_("Allocated volume ({0} KL) would exceed the {1} KL actually received on {2}.").format(
					already_allocated + flt(self.allocated_quantity_kl), received, self.reconciliation
				)
			)
		if flt(self.allocated_quantity_kl) > nominated:
			frappe.throw(
				_("Allocated quantity ({0} KL) cannot exceed Nomination {1}'s nominated quantity ({2} KL).").format(
					self.allocated_quantity_kl, self.nomination, nominated
				)
			)

	def on_submit(self):
		log_journey_step(self.journey_ref, "10. Allocation", self)
