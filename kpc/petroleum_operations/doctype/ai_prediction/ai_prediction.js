// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Prediction", {
	refresh(frm) {
		const colors = { "Immediate (<24h)": "red", "7 Days": "orange", "30 Days": "yellow", "90 Days": "blue" };
		frm.page.clear_indicator();
		if (frm.doc.risk_horizon) {
			frm.page.set_indicator(frm.doc.risk_horizon, colors[frm.doc.risk_horizon] || "blue");
		}
	},
});
