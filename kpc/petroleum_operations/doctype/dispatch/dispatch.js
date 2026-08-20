// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Dispatch", {
	setup(frm) {
		frm.set_query("allocation", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("destination_tank", () => ({ filters: { current_state: "Active" } }));
	},
});
