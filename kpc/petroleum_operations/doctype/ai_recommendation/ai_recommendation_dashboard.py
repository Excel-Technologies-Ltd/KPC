# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "ai_recommendation",
		"transactions": [
			{"label": _("Execution"), "items": ["Maintenance Work Order"]},
		],
	}
