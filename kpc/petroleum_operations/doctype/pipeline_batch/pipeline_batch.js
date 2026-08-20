// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pipeline Batch", {
	setup(frm) {
		frm.set_query("nomination", () => ({ filters: { docstatus: 1 } }));
	},

	refresh(frm) {
		if (frm.doc.journey_ref) {
			frm.add_custom_button(__("View Golden Thread"), () => {
				frappe.set_route("Form", "Journey", frm.doc.journey_ref);
			});
		}
	},
});
