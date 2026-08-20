# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "tariff",
		"internal_links": {"Invoice": ["lines", "tariff"]},
		"transactions": [
			{"label": _("Billing"), "items": ["Invoice"]},
		],
	}
