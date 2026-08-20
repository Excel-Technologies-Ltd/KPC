# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Integration with standard ERPNext Accounts.

Deliberately thin: this module never writes a GL Entry itself. It builds a
standard Sales Invoice from a KPC Invoice's rated lines and lets ERPNext's
own Sales Invoice controller do everything it already does well (tax/COA
validation, GL Entry creation, customer ledger, financial reports). The only
thing added on top is making sure journey_ref - the Golden Thread - rides
along onto the Sales Invoice and, from there, onto its GL Entries.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def create_and_submit_sales_invoice(kpc_invoice) -> frappe.model.document.Document:
	"""Build a standard Sales Invoice from a KPC Invoice's rated lines,
	submit it (triggering ERPNext's own GL Entry creation), and return it.
	"""
	items = []
	for line in kpc_invoice.lines:
		income_account = resolve_income_account(line.product, kpc_invoice.company)
		item_row = {
			"item_code": line.product,
			"qty": flt(line.quantity_kl),
			"uom": "Kilolitre",
			"conversion_factor": 1,
			"rate": flt(line.rate_per_kl),
			"income_account": income_account,
			"cost_center": resolve_cost_center(kpc_invoice.company),
		}
		item_row.update(_delivery_reference(line.dispatch))
		items.append(item_row)

	sales_invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": kpc_invoice.customer,
			"company": kpc_invoice.company,
			"currency": kpc_invoice.currency,
			"posting_date": kpc_invoice.posting_date,
			"journey_ref": kpc_invoice.journey_ref,
			"items": items,
		}
	)
	sales_invoice.insert()
	sales_invoice.submit()
	return sales_invoice


def _delivery_reference(dispatch: str) -> dict:
	"""Every Dispatch (Step 11) already created and submitted its own
	Delivery Note before Invoice (Step 12) ever runs - reference that
	Delivery Note row here so ERPNext treats this Sales Invoice line as
	billing against an already-delivered consignment (correct % Delivered
	/ % Billed tracking) rather than an independent, undelivered sale.
	"""
	delivery_note = frappe.db.get_value("Dispatch", dispatch, "delivery_note")
	if not delivery_note:
		return {}

	dn_detail = frappe.db.get_value("Delivery Note Item", {"parent": delivery_note}, "name")
	return {"delivery_note": delivery_note, "dn_detail": dn_detail}


def resolve_income_account(item_code: str, company: str) -> str:
	"""Item Default (per item, per company) first, falling back to the
	Company's default income account, falling back to the first standalone
	Income account on the Company's chart of accounts. Raising a clear error
	beats letting Sales Invoice fail deep inside ERPNext's own validation
	with a less specific message.
	"""
	item_default = frappe.db.get_value(
		"Item Default", {"parent": item_code, "company": company}, "income_account"
	)
	if item_default:
		return item_default

	company_default = frappe.db.get_value("Company", company, "default_income_account")
	if company_default:
		return company_default

	fallback = frappe.db.get_value(
		"Account", {"company": company, "root_type": "Income", "is_group": 0}, "name", order_by="name"
	)
	if fallback:
		return fallback

	frappe.throw(
		_(
			"No Income Account is configured for Item {0} or Company {1}. Set one on the Item's "
			"Accounting defaults (per Company) before invoicing."
		).format(item_code, company)
	)


def resolve_cost_center(company: str) -> str:
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	if cost_center:
		return cost_center

	fallback = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name", order_by="name")
	if fallback:
		return fallback

	frappe.throw(_("No default Cost Center is configured for Company {0}.").format(company))


def propagate_journey_ref_to_gl_entries(doc, method=None):
	"""doc_events hook: Sales Invoice.on_submit.

	Runs after ERPNext's own on_submit has already created the GL Entries
	(doc_events fire after the doctype's own controller method), so this is
	purely a bulk UPDATE stamping journey_ref onto rows that already exist -
	it never decides what to post, only labels what ERPNext already posted.
	"""
	journey_ref = doc.get("journey_ref")
	if not journey_ref:
		return

	frappe.db.set_value(
		"GL Entry", {"voucher_type": "Sales Invoice", "voucher_no": doc.name}, "journey_ref", journey_ref
	)


def reverse_financial_posting(doc, method=None):
	"""doc_events hook: Sales Invoice.on_cancel.

	Stamps journey_ref onto the reversal GL Entries too, and flips the
	corresponding Financial Posting to Reversed so the Golden Thread shows
	the cancellation, not just silence.
	"""
	journey_ref = doc.get("journey_ref")
	if not journey_ref:
		return

	frappe.db.set_value(
		"GL Entry", {"voucher_type": "Sales Invoice", "voucher_no": doc.name}, "journey_ref", journey_ref
	)

	financial_posting = frappe.db.get_value("Financial Posting", {"sales_invoice": doc.name})
	if not financial_posting:
		return

	from kpc.petroleum_operations.utils import log_journey_step

	fp = frappe.get_doc("Financial Posting", financial_posting)
	fp.db_set("status", "Reversed", update_modified=False)
	log_journey_step(journey_ref, "13. Financial Posting", fp)
