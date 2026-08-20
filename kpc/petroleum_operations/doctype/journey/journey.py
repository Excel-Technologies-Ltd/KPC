# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Journey(Document):
	"""The Golden Thread master. Every transaction doctype in the 13-step
	KPC workflow links back here via a mandatory ``journey_ref`` field, and
	registers itself through ``kpc.petroleum_operations.utils.log_journey_step``
	so this document accumulates a complete, ordered audit trail.

	Journey records themselves are never edited directly by end users
	(read-only fields, log appended only through the shared helper) -
	they are a system-maintained ledger.
	"""

	pass
