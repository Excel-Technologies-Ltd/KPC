// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Terminal Receipt", {
	setup(frm) {
		frm.set_query("movement", () => ({ filters: { movement_status: ["in", ["In Transit", "Completed"]] } }));
	},

	movement(frm) {
		if (!frm.doc.movement) return;
		frappe.db.get_value("Movement", frm.doc.movement, "destination_terminal").then((r) => {
			if (!r.message || !r.message.destination_terminal) return;
			frm.set_query("destination_tank", () => ({
				filters: { terminal: r.message.destination_terminal, current_state: "Active" },
			}));
		});
	},
});
