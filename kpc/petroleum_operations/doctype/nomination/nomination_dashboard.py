# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "nomination",
		"transactions": [
			{"label": _("Fulfillment"), "items": ["Pipeline Batch", "Allocation"]},
		],
	}
