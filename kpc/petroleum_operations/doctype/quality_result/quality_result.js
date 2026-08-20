// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Result", {
	refresh(frm) {
		frm.trigger("set_indicator");
	},

	set_indicator(frm) {
		const colors = { Pending: "orange", Accepted: "green", Quarantined: "red" };
		frm.page.clear_indicator();
		if (frm.doc.workflow_state) {
			frm.page.set_indicator(frm.doc.workflow_state, colors[frm.doc.workflow_state] || "blue");
		}
	},
});

frappe.ui.form.on("Quality Parameter Result", {
	result_value(frm, cdt, cdn) {
		frm.trigger("refresh_row_flag", cdt, cdn);
	},
	specification_min(frm, cdt, cdn) {
		frm.trigger("refresh_row_flag", cdt, cdn);
	},
	specification_max(frm, cdt, cdn) {
		frm.trigger("refresh_row_flag", cdt, cdn);
	},
	refresh_row_flag(frm, cdt, cdn) {
		// Server recalculates authoritatively on save; this is a live hint only.
		const row = locals[cdt][cdn];
		let within = true;
		if (row.specification_min && row.result_value < row.specification_min) within = false;
		if (row.specification_max && row.result_value > row.specification_max) within = false;
		frappe.model.set_value(cdt, cdn, "is_within_spec", within ? 1 : 0);
	},
});
