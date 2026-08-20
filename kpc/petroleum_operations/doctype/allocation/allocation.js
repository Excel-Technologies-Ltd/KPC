// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Allocation", {
	setup(frm) {
		frm.set_query("nomination", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("reconciliation", () => ({ filters: { docstatus: 1 } }));
	},

	reconciliation(frm) {
		if (!frm.doc.reconciliation) return;
		frappe.db.get_value("Reconciliation", frm.doc.reconciliation, "received_quantity_kl").then((r) => {
			if (r.message && r.message.received_quantity_kl && !frm.doc.allocated_quantity_kl) {
				frm.set_value("allocated_quantity_kl", r.message.received_quantity_kl);
			}
		});
	},
});
