// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Variance", {
	refresh(frm) {
		const colors = { "Pending Approval": "orange", Approved: "green", Rejected: "red" };
		frm.page.clear_indicator();
		if (frm.doc.workflow_state) {
			frm.page.set_indicator(frm.doc.workflow_state, colors[frm.doc.workflow_state] || "blue");
		}
	},
});
