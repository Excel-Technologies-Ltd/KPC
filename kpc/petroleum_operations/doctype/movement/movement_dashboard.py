# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "movement",
		"transactions": [
			{
				"label": _("AI Predictive Maintenance"),
				"items": ["AI Alert", "AI Prediction", "AI Recommendation", "Maintenance Work Order"],
			},
			{"label": _("Delivery"), "items": ["Terminal Receipt"]},
		],
	}
