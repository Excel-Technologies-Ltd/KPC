# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.utils import (
	assert_tank_available,
	calculate_standard_volume,
	log_journey_step,
	record_inventory_movement,
)


class TerminalReceipt(Document):
	def validate(self):
		self.validate_tank_state()
		self.apply_standard_volume()
		self.fetch_dispatched_quantity()

	def validate_tank_state(self):
		tank = frappe.get_doc("Oil Tank", self.destination_tank)
		self.tank_state_at_receipt = tank.current_state
		assert_tank_available(self.destination_tank, action=_("confirm receipt into"))

	def apply_standard_volume(self):
		result = calculate_standard_volume(
			self.destination_tank,
			self.observed_level_mm,
			self.water_dip_mm,
			self.density_at_15c,
			self.observed_temperature_c,
		)
		self.gross_observed_volume_kl = result["gross_observed_volume_kl"]
		self.volume_correction_factor = result["volume_correction_factor"]
		self.net_standard_volume_kl = result["net_standard_volume_kl"]

	def fetch_dispatched_quantity(self):
		pipeline_batch = frappe.db.get_value("Movement", self.movement, "pipeline_batch")
		if pipeline_batch:
			self.dispatched_quantity_kl = flt(
				frappe.db.get_value("Pipeline Batch", pipeline_batch, "planned_volume_kl")
			)

	def on_submit(self):
		log_journey_step(self.journey_ref, "8. Terminal Receipt", self)
		# stock_owner left blank: this arrives as KPC custody stock and only
		# becomes customer-owned once Allocation (Step 10) assigns it.
		record_inventory_movement(
			self.destination_tank, self.journey_ref, receipts_kl=self.net_standard_volume_kl
		)
