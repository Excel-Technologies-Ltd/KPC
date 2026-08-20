# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.utils import log_journey_step


class Nomination(Document):
	def validate(self):
		self.validate_quality_release()

	def validate_quality_release(self):
		"""Product cannot be nominated until it has cleared quality release -
		a Nomination against ungraded or quarantined stock is a data-integrity
		error, not just a business preference."""
		latest_qr = frappe.get_all(
			"Quality Result",
			filters={"journey_ref": self.journey_ref},
			fields=["workflow_state"],
			order_by="creation desc",
			limit=1,
		)
		if not latest_qr:
			frappe.throw(
				_("No Quality Result found for Journey {0}. Product must be quality-released before nomination.").format(
					self.journey_ref
				)
			)
		if latest_qr[0].workflow_state != "Accepted":
			frappe.throw(
				_("Journey {0} is not quality-released (latest Quality Result is '{1}').").format(
					self.journey_ref, latest_qr[0].workflow_state
				)
			)

	def before_submit(self):
		"""'Accepting' a Nomination = submitting it. Both mandated checks -
		credit and stock ownership - run here and hard-block the submit."""
		self.validate_credit_limit()
		self.validate_stock_ownership()

	def validate_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		# Tariffs don't exist until Phase 5 (Invoice), so the exposure used
		# here is a provisional estimate off the Item's standard rate - it
		# will be superseded by actual billed value once Invoicing lands.
		rate = flt(frappe.db.get_value("Item", self.product, "standard_rate"))
		estimated_value = flt(self.nominated_quantity_kl) * rate

		try:
			check_credit_limit(self.customer, self.company, extra_amount=estimated_value)
		except frappe.ValidationError:
			self.credit_status = "Exceeds Limit"
			raise
		self.credit_status = "Within Limit"

	def validate_stock_ownership(self):
		position = frappe.get_all(
			"Inventory Position",
			filters={"journey_ref": self.journey_ref},
			fields=["name", "closing_volume_kl", "stock_owner"],
			order_by="position_date desc, creation desc",
			limit=1,
		)
		if not position:
			self.ownership_status = "Insufficient Stock"
			frappe.throw(
				_("No Inventory Position recorded for Journey {0}; cannot confirm stock ownership.").format(
					self.journey_ref
				)
			)

		position = position[0]
		if position.stock_owner and position.stock_owner != self.customer:
			self.ownership_status = "Insufficient Stock"
			frappe.throw(
				_("Stock under Journey {0} is owned by {1}, not {2}.").format(
					self.journey_ref, position.stock_owner, self.customer
				)
			)
		if flt(position.closing_volume_kl) < flt(self.nominated_quantity_kl):
			self.ownership_status = "Insufficient Stock"
			frappe.throw(
				_("Nominated quantity ({0} KL) exceeds available stock ({1} KL) for Journey {2}.").format(
					self.nominated_quantity_kl, position.closing_volume_kl, self.journey_ref
				)
			)
		self.ownership_status = "Confirmed"

	def on_submit(self):
		log_journey_step(self.journey_ref, "5. Nomination", self)
