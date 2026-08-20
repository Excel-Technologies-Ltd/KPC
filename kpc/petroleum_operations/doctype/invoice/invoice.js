// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Invoice", {
	setup(frm) {
		frm.set_query("lines", "dispatch", () => ({ filters: { docstatus: 1 } }));
	},

	refresh(frm) {
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("View Sales Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			});
		}
		if (frm.doc.journey_ref) {
			frm.add_custom_button(__("View Golden Thread"), () => {
				frappe.set_route("Form", "Journey", frm.doc.journey_ref);
			});
		}
	},
});

frappe.ui.form.on("Invoice Line", {
	dispatch(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.dispatch) return;
		frappe.db.get_value("Dispatch", row.dispatch, "dispatched_quantity_kl").then((r) => {
			if (r.message) {
				frappe.model.set_value(cdt, cdn, "quantity_kl", r.message.dispatched_quantity_kl);
			}
		});
	},

	tariff(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.tariff) return;
		frappe.db.get_value("Tariff", row.tariff, ["product", "rate_per_kl"]).then((r) => {
			if (r.message) {
				frappe.model.set_value(cdt, cdn, "product", r.message.product);
				frappe.model.set_value(cdt, cdn, "rate_per_kl", r.message.rate_per_kl);
			}
		});
	},
});
