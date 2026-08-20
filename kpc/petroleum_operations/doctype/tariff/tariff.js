// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tariff", {
	refresh(frm) {
		if (!frm.doc.is_active) {
			frm.dashboard.set_headline_alert(__("This tariff is inactive and will not be selectable on new Invoices."), "orange");
		}
	},
});
