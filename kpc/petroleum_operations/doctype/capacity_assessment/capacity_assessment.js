// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Capacity Assessment", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Recalculate Committed Volume"), () => {
				frm.call("refresh_commitment").then(() => frm.refresh());
			});
		}
	},
});
