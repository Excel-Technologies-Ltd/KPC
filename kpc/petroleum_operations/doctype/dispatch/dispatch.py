# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.integrations.stock import create_and_submit_delivery_note
from kpc.petroleum_operations.utils import assert_tank_available, log_journey_step, record_inventory_movement


class Dispatch(Document):
	def validate(self):
		self.validate_allocation_confirmed()
		self.validate_tank_state()
		self.validate_quantity()

	def validate_allocation_confirmed(self):
		if frappe.db.get_value("Allocation", self.allocation, "docstatus") != 1:
			frappe.throw(_("Allocation {0} must be confirmed before it can be dispatched.").format(self.allocation))

	def validate_tank_state(self):
		assert_tank_available(self.destination_tank, action=_("dispatch from"))

	def validate_quantity(self):
		allocated = flt(frappe.db.get_value("Allocation", self.allocation, "allocated_quantity_kl"))

		already_dispatched = flt(
			frappe.db.sql(
				"""
				select coalesce(sum(dispatched_quantity_kl), 0)
				from `tabDispatch`
				where allocation = %s and docstatus < 2 and name != %s
				""",
				(self.allocation, self.name or ""),
			)[0][0]
		)

		if already_dispatched + flt(self.dispatched_quantity_kl) > allocated:
			frappe.throw(
				_("Dispatched volume ({0} KL) would exceed Allocation {1}'s allocated quantity ({2} KL).").format(
					already_dispatched + flt(self.dispatched_quantity_kl), self.allocation, allocated
				)
			)

	def before_submit(self):
		"""The Delivery Note *is* the delivery chalan - created here so it
		lands in the same submit as this Dispatch, rather than requiring a
		separate manual 'Create > Delivery Note' step against a Sales
		Invoice that doesn't exist yet (Invoice/Step 12 comes after
		Dispatch/Step 11)."""
		delivery_note = create_and_submit_delivery_note(self)
		self.delivery_note = delivery_note.name

	def on_submit(self):
		log_journey_step(self.journey_ref, "11. Dispatch", self)
		record_inventory_movement(
			self.destination_tank,
			self.journey_ref,
			stock_owner=self.customer,
			dispatches_kl=self.dispatched_quantity_kl,
		)

	def on_cancel(self):
		"""Same link-integrity reasoning as Invoice/Sales Invoice: cancel the
		Delivery Note through cancelling this Dispatch, not the other way
		round."""
		if self.delivery_note and frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus") == 1:
			frappe.get_doc("Delivery Note", self.delivery_note).cancel()
