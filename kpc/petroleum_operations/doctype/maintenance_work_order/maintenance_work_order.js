// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Work Order", {
	onload(frm) {
		if (frm.is_new() && frm.doc.ai_recommendation) {
			frm.trigger("ai_recommendation");
		}
	},

	ai_recommendation(frm) {
		if (!frm.doc.ai_recommendation) return;
		frappe.db.get_value("AI Recommendation", frm.doc.ai_recommendation, [
			"journey_ref",
			"recommended_action",
			"details",
			"priority",
		]).then((r) => {
			const v = r.message || {};
			if (v.journey_ref) frm.set_value("journey_ref", v.journey_ref);
			if (v.recommended_action) {
				frm.set_value(
					"description",
					`${v.recommended_action}${v.details ? " - " + v.details : ""} (Priority: ${v.priority || "-"})`
				);
			}
		});
	},

	refresh(frm) {
		const colors = { "Not Started": "grey", "In Progress": "orange", Completed: "green" };
		frm.page.clear_indicator();
		if (frm.doc.execution_status) {
			frm.page.set_indicator(frm.doc.execution_status, colors[frm.doc.execution_status] || "blue");
		}
	},
});
