// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Journey", {
	refresh(frm) {
		frm.disable_form();
		frm.dashboard.set_headline(
			__("Golden Thread record - system maintained. Every step of {0} is logged below.", [
				frm.doc.name,
			])
		);
	},
});
