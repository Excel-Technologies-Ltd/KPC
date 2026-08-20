// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Oil Shipment", {
	refresh(frm) {
		frm.trigger("set_indicator");

		if (frm.doc.journey_ref) {
			frm.add_custom_button(__("View Golden Thread"), () => {
				frappe.set_route("Form", "Journey", frm.doc.journey_ref);
			});
		}
	},

	set_indicator(frm) {
		const colors = {
			Draft: "grey",
			"Vessel Arrived": "blue",
			Discharging: "orange",
			Received: "green",
			Cancelled: "red",
		};
		frm.page.clear_indicator();
		if (frm.doc.workflow_state) {
			frm.page.set_indicator(frm.doc.workflow_state, colors[frm.doc.workflow_state] || "blue");
		}
	},
});
