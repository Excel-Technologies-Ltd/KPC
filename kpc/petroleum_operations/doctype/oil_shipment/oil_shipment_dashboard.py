# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "shipment",
		"transactions": [
			{"label": _("Receipt & Quality"), "items": ["Tank Measurement", "Quality Result"]},
		],
	}
