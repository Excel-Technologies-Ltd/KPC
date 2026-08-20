// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Terminal", {
	refresh(frm) {
		frm.trigger("set_indicator");
	},

	is_active(frm) {
		frm.trigger("set_indicator");
	},

	set_indicator(frm) {
		frm.dashboard.clear_headline();
		if (!frm.doc.is_active) {
			frm.dashboard.set_headline_alert(
				__("This terminal is marked inactive and should not be used for new shipments."),
				"orange"
			);
		}
	},
});
