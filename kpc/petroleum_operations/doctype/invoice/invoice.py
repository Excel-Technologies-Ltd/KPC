# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from kpc.petroleum_operations.integrations.accounts import create_and_submit_sales_invoice
from kpc.petroleum_operations.utils import log_journey_step


class Invoice(Document):
	def validate(self):
		self.apply_lines()
		self.calculate_grand_total()

	def apply_lines(self):
		"""Map dispatched quantities to billing: each line prices one
		Dispatch against a Tariff. Every field here is either fetched
		(trustworthy, from the doctypes that produced the actual physical
		movement) or computed - none of it is free-typed by the user."""
		if not self.lines:
			frappe.throw(_("At least one rated line (Dispatch + Tariff) is required."))

		invoiced_dispatches = self.already_invoiced_dispatches()

		for line in self.lines:
			dispatch = frappe.db.get_value(
				"Dispatch", line.dispatch, ["journey_ref", "customer", "docstatus"], as_dict=True
			)
			if not dispatch or dispatch.docstatus != 1:
				frappe.throw(_("Dispatch {0} must be submitted before it can be invoiced.").format(line.dispatch))
			if dispatch.journey_ref != self.journey_ref:
				frappe.throw(
					_("Dispatch {0} belongs to Journey {1}, not this Invoice's Journey {2}.").format(
						line.dispatch, dispatch.journey_ref, self.journey_ref
					)
				)
			if dispatch.customer != self.customer:
				frappe.throw(_("Dispatch {0} was allocated to a different customer.").format(line.dispatch))
			if line.dispatch in invoiced_dispatches:
				frappe.throw(
					_("Dispatch {0} is already billed on Invoice {1}.").format(
						line.dispatch, invoiced_dispatches[line.dispatch]
					)
				)

			line.quantity_kl = frappe.db.get_value("Dispatch", line.dispatch, "dispatched_quantity_kl")

			tariff = frappe.db.get_value(
				"Tariff", line.tariff, ["product", "rate_per_kl", "is_active"], as_dict=True
			)
			if not tariff or not tariff.is_active:
				frappe.throw(_("Tariff {0} is not active.").format(line.tariff))

			line.product = tariff.product
			line.rate_per_kl = tariff.rate_per_kl
			self.validate_kilolitre_uom(line.product)
			line.amount = flt(flt(line.quantity_kl) * flt(line.rate_per_kl), 2)

	def already_invoiced_dispatches(self) -> dict:
		rows = frappe.db.sql(
			"""
			select il.dispatch, il.parent
			from `tabInvoice Line` il
			inner join `tabInvoice` inv on inv.name = il.parent
			where inv.docstatus < 2 and inv.name != %s
			""",
			(self.name or "",),
			as_dict=True,
		)
		return {row.dispatch: row.parent for row in rows}

	@staticmethod
	def validate_kilolitre_uom(item_code: str) -> None:
		"""Every calculation in this app - and this bill - is in KL. Require
		the Item's stock UOM to match rather than silently guessing a unit
		conversion factor that could quietly under- or over-bill a customer."""
		stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
		if stock_uom != "Kilolitre":
			frappe.throw(
				_(
					"Product {0} has stock UOM '{1}'. Petroleum products must be stocked in 'Kilolitre' "
					"for billing quantities to be correct - update the Item before invoicing."
				).format(item_code, stock_uom)
			)

	def calculate_grand_total(self):
		self.grand_total = flt(sum(flt(line.amount) for line in self.lines), 2)

	def before_submit(self):
		"""Create and submit the real ERPNext Sales Invoice as part of this
		same submit - if Accounts setup is incomplete (missing income
		account, etc.) the whole Invoice submit aborts rather than leaving a
		KPC Invoice submitted with no corresponding GL posting."""
		sales_invoice = create_and_submit_sales_invoice(self)
		self.sales_invoice = sales_invoice.name

	def on_submit(self):
		log_journey_step(self.journey_ref, "12. Invoice", self)
		self.create_financial_posting()

	def create_financial_posting(self):
		sales_invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
		gl_entry_count = frappe.db.count(
			"GL Entry", {"voucher_type": "Sales Invoice", "voucher_no": self.sales_invoice}
		)

		posting = frappe.get_doc(
			{
				"doctype": "Financial Posting",
				"journey_ref": self.journey_ref,
				"invoice": self.name,
				"sales_invoice": self.sales_invoice,
				"posting_date": sales_invoice.posting_date or today(),
				"currency": self.currency,
				"total_amount": sales_invoice.grand_total,
				"gl_entry_count": gl_entry_count,
				"status": "Posted",
			}
		)
		posting.insert(ignore_permissions=True)
		log_journey_step(self.journey_ref, "13. Financial Posting", posting)

	def on_cancel(self):
		"""Cancelling the Sales Invoice directly is blocked by Frappe's own
		link-integrity check (this Invoice still links to it) - which is the
		right protection, but it means the Sales Invoice must be cancelled
		*through* cancelling this Invoice, not the other way round. Doing so
		here also fires the Sales Invoice's own on_cancel doc_event (see
		integrations.accounts.reverse_financial_posting), which flips the
		Financial Posting to Reversed and stamps journey_ref onto the
		reversal GL Entries."""
		if self.sales_invoice and frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus") == 1:
			frappe.get_doc("Sales Invoice", self.sales_invoice).cancel()
