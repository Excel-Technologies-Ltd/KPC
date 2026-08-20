// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Posting", {
	refresh(frm) {
		frm.disable_form();

		const colors = { Posted: "green", Reversed: "red" };
		frm.page.clear_indicator();
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "blue");
		}

		frm.add_custom_button(__("View Sales Invoice"), () => {
			frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
		});
		frm.add_custom_button(__("View Golden Thread"), () => {
			frappe.set_route("Form", "Journey", frm.doc.journey_ref);
		});
	},
});
