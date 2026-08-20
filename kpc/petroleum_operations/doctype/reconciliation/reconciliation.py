# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from kpc.petroleum_operations.integrations.stock import post_material_issue, resolve_origin_tank
from kpc.petroleum_operations.utils import log_journey_step


class Reconciliation(Document):
	def validate(self):
		self.calculate_variance()

	def calculate_variance(self):
		"""Auto-calculate loss/variance, as the brief requires. Positive
		variance_kl = less arrived than left (a loss); negative = more
		arrived than dispatched (a metrology quirk, not necessarily a gain
		to celebrate, but recorded honestly either way)."""
		dispatched = flt(self.dispatched_quantity_kl)
		received = flt(self.received_quantity_kl)

		self.variance_kl = flt(dispatched - received, 3)
		self.variance_percent = flt((self.variance_kl / dispatched) * 100, 3) if dispatched else 0.0
		self.within_tolerance = abs(self.variance_percent) <= flt(self.tolerance_percent)

	def before_submit(self):
		"""'Accepting' a Reconciliation = submitting it. Block outright if the
		variance is outside tolerance and nobody has explained why."""
		if not self.within_tolerance and not (self.justification or "").strip():
			frappe.throw(
				_(
					"Variance of {0}% exceeds the {1}% tolerance. A justification is required before this "
					"Reconciliation can be accepted."
				).format(self.variance_percent, self.tolerance_percent)
			)
		self.reconciled_by = frappe.session.user
		self.reconciled_on = now_datetime()

	def on_submit(self):
		log_journey_step(self.journey_ref, "9. Reconciliation", self)
		self.post_transit_loss()

	def post_transit_loss(self):
		"""A positive variance is a real physical loss - now that it's
		fiscally recognised (accepted, with justification if it needed
		one), recognise it in the Stock Ledger too, drawn from the origin
		tank it left. Gains (negative variance) aren't posted here - a
		metrology quirk isn't stock a KPC tank actually gained."""
		if self.variance_kl <= 0:
			return

		origin_tank_name = resolve_origin_tank(self.journey_ref)
		origin_tank = frappe.get_doc("Oil Tank", origin_tank_name)
		movement = frappe.db.get_value("Terminal Receipt", self.terminal_receipt, "movement")
		product = frappe.db.get_value("Movement", movement, "product")

		post_material_issue(origin_tank.warehouse, product, self.variance_kl, self.journey_ref)
