// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Alert", {
	refresh(frm) {
		const colors = { Low: "yellow", Medium: "orange", High: "red", Critical: "red" };
		frm.page.clear_indicator();
		if (frm.doc.severity) {
			frm.page.set_indicator(frm.doc.severity, colors[frm.doc.severity] || "blue");
		}
		if (frm.doc.movement) {
			frm.add_custom_button(__("View Movement"), () => {
				frappe.set_route("Form", "Movement", frm.doc.movement);
			});
		}
	},
});
