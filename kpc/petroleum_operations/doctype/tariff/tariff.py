# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff


class Tariff(Document):
	def validate(self):
		if self.effective_to and date_diff(self.effective_to, self.effective_from) < 0:
			frappe.throw(_("Effective To cannot be before Effective From."))
