// Copyright (c) 2026, ArcApps and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tank Measurement", {
	setup(frm) {
		frm.set_query("tank", () => ({ filters: { current_state: "Active" } }));
	},

	journey_ref(frm) {
		if (!frm.doc.journey_ref) return;
		frappe.db.get_value("Journey", frm.doc.journey_ref, "origin_shipment").then((r) => {
			if (r.message && r.message.origin_shipment) {
				frm.set_value("shipment", r.message.origin_shipment);
			}
		});
	},

	shipment(frm) {
		if (!frm.doc.shipment) return;
		frappe.db.get_value("Oil Shipment", frm.doc.shipment, "product").then((r) => {
			if (r.message && r.message.product) {
				frm.trigger("fetch_density");
			}
		});
	},

	tank(frm) {
		if (!frm.doc.tank) return;
		frappe.db.get_value("Oil Tank", frm.doc.tank, "current_state").then((r) => {
			if (r.message && ["Maintenance", "Quarantine", "Decommissioned"].includes(r.message.current_state)) {
				frappe.msgprint({
					title: __("Tank Unavailable"),
					indicator: "orange",
					message: __("Tank {0} is currently {1}. Opening/Closing readings will be blocked on save.", [
						frm.doc.tank,
						r.message.current_state,
					]),
				});
			}
		});
	},

	fetch_density(frm) {
		if (!frm.doc.shipment) return;
		frappe.db.get_value("Oil Shipment", frm.doc.shipment, "product").then((r) => {
			const product = r.message && r.message.product;
			if (!product) return;
			frappe.db.get_value("Item", product, "density_at_15c").then((res) => {
				if (res.message && res.message.density_at_15c) {
					frm.set_value("density_at_15c", res.message.density_at_15c);
				}
			});
		});
	},
});
