# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
from frappe import _


def get_data():
	return {
		"fieldname": "terminal",
		"transactions": [
			{"label": _("Storage"), "items": ["Oil Tank"]},
			{"label": _("Shipments"), "items": ["Oil Shipment"]},
		],
	}
