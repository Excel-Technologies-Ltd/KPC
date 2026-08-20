// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inventory Position", {
	opening_volume_kl(frm) {
		frm.trigger("recalculate");
	},
	receipts_kl(frm) {
		frm.trigger("recalculate");
	},
	dispatches_kl(frm) {
		frm.trigger("recalculate");
	},
	adjustments_kl(frm) {
		frm.trigger("recalculate");
	},
	recalculate(frm) {
		// Live preview only; the server recalculates authoritatively on save.
		const closing =
			flt(frm.doc.opening_volume_kl) +
			flt(frm.doc.receipts_kl) -
			flt(frm.doc.dispatches_kl) +
			flt(frm.doc.adjustments_kl);
		frm.set_value("closing_volume_kl", closing);
	},
});
