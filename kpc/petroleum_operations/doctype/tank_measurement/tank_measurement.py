# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.integrations.stock import post_material_receipt
from kpc.petroleum_operations.utils import assert_tank_available, calculate_standard_volume, log_journey_step


class TankMeasurement(Document):
	def validate(self):
		self.validate_tank_state()
		self.apply_standard_volume()

	def validate_tank_state(self):
		tank = frappe.get_doc("Oil Tank", self.tank)
		self.tank_state_at_measurement = tank.current_state

		# Only Opening/Closing readings represent a custody-transfer event
		# (receipt/dispatch confirmation); Interim/Daily Gauge readings are
		# informational and are allowed even while a tank is quarantined so
		# operators can keep monitoring it.
		if self.measurement_type in ("Opening", "Closing"):
			assert_tank_available(self.tank, action=_("confirm a {0} reading").format(self.measurement_type))

	def apply_standard_volume(self):
		if not self.tank:
			return

		result = calculate_standard_volume(
			self.tank, self.observed_level_mm, self.water_dip_mm, self.density_at_15c, self.observed_temperature_c
		)
		self.gross_observed_volume_kl = result["gross_observed_volume_kl"]
		self.volume_correction_factor = result["volume_correction_factor"]
		self.net_standard_volume_kl = result["net_standard_volume_kl"]

	def on_submit(self):
		log_journey_step(self.journey_ref, "2. Receipt", self)
		self.post_stock_receipt()

	def post_stock_receipt(self):
		"""A Closing reading is the confirmed-received event for this tank -
		post it into the ERPNext Stock Ledger via the tank's Warehouse, so
		the physical custody chain and the ERPNext stock ledger agree from
		the very first step."""
		if self.measurement_type != "Closing":
			return

		tank = frappe.get_doc("Oil Tank", self.tank)
		product = frappe.db.get_value("Oil Shipment", self.shipment, "product")

		# Illustrative valuation only, for the very first stock movement of
		# this item (ERPNext needs a basic_rate with no prior stock
		# history) - a real deployment would use a landed-cost figure.
		rate = flt(frappe.db.get_value("Item", product, "standard_rate")) or None

		post_material_receipt(tank.warehouse, product, self.net_standard_volume_kl, self.journey_ref, rate=rate)
