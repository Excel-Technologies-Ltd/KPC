# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "dispatch",
		# Invoice references Dispatch from inside its child table (Invoice
		# Line), not a direct field on Invoice itself - internal_links tells
		# the dashboard which child table ("lines") and which field within
		# it ("dispatch") to follow.
		"internal_links": {"Invoice": ["lines", "dispatch"]},
		"transactions": [
			{"label": _("Billing"), "items": ["Invoice"]},
		],
	}
