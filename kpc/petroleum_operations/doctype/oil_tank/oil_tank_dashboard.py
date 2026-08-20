# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "tank",
		"non_standard_fieldnames": {
			"Terminal Receipt": "destination_tank",
			"Dispatch": "destination_tank",
		},
		"transactions": [
			{"label": _("Gauging & Quality"), "items": ["Tank Measurement", "Quality Result"]},
			{"label": _("Stock"), "items": ["Inventory Position"]},
			{"label": _("Movements"), "items": ["Terminal Receipt", "Dispatch"]},
		],
	}
