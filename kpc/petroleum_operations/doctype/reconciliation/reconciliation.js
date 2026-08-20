// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reconciliation", {
	refresh(frm) {
		if (frm.doc.variance_percent && !frm.doc.within_tolerance) {
			frm.dashboard.set_headline_alert(
				__("Variance of {0}% exceeds the {1}% tolerance - a justification is required to accept this Reconciliation.", [
					frm.doc.variance_percent,
					frm.doc.tolerance_percent,
				]),
				"red"
			);
		}
	},
});
