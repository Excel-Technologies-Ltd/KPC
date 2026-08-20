// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Oil Tank", {
	refresh(frm) {
		frm.trigger("set_state_indicator");
	},

	current_state(frm) {
		frm.trigger("set_state_indicator");
	},

	set_state_indicator(frm) {
		const colors = {
			Active: "green",
			Maintenance: "orange",
			Quarantine: "red",
			Decommissioned: "darkgrey",
		};
		frm.page.clear_indicator();
		if (frm.doc.current_state) {
			frm.page.set_indicator(frm.doc.current_state, colors[frm.doc.current_state] || "blue");
		}
		if (["Maintenance", "Quarantine", "Decommissioned"].includes(frm.doc.current_state)) {
			frm.dashboard.set_headline_alert(
				__("This tank is {0}. New receipts/dispatches against it will be blocked.", [
					frm.doc.current_state,
				]),
				"red"
			);
		} else {
			frm.dashboard.clear_headline();
		}
	},
});
