// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Recommendation", {
	refresh(frm) {
		const colors = { "Pending Approval": "orange", Approved: "green", Rejected: "red" };
		frm.page.clear_indicator();
		if (frm.doc.workflow_state) {
			frm.page.set_indicator(frm.doc.workflow_state, colors[frm.doc.workflow_state] || "blue");
		}
		if (frm.doc.workflow_state === "Approved") {
			frm.add_custom_button(__("Create Maintenance Work Order"), () => {
				frappe.new_doc("Maintenance Work Order", { ai_recommendation: frm.doc.name });
			});
		}
	},
});
