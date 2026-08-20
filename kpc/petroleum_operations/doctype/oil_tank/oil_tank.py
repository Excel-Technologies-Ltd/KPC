# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from kpc.petroleum_operations.integrations.stock import get_or_create_tank_warehouse


class OilTank(Document):
	def before_insert(self):
		self.warehouse = get_or_create_tank_warehouse(self)

	def validate(self):
		self.validate_capacity()
		self.stamp_state_change()

	def validate_capacity(self):
		if self.safe_fill_capacity_kl and self.safe_fill_capacity_kl > self.capacity_kl:
			frappe.throw(
				_("Safe Fill Capacity ({0} KL) cannot exceed Shell Capacity ({1} KL).").format(
					self.safe_fill_capacity_kl, self.capacity_kl
				)
			)
		if self.dead_stock_kl and self.dead_stock_kl >= self.capacity_kl:
			frappe.throw(_("Dead Stock (KL) must be less than Shell Capacity (KL)."))

	def stamp_state_change(self):
		"""Record when/who last changed the operational state, so Tank
		Measurement/Inventory Position can show a clear audit trail for why
		a tank was blocked at a given point in time."""
		if self.is_new() or self.has_value_changed("current_state"):
			self.state_changed_on = now_datetime()
			self.state_changed_by = frappe.session.user
