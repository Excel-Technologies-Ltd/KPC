# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt

from kpc.petroleum_operations.utils import assert_tank_available, log_journey_step


class InventoryPosition(Document):
	def validate(self):
		self.validate_tank_state()
		self.calculate_closing_volume()

	def validate_tank_state(self):
		if flt(self.receipts_kl) > 0:
			assert_tank_available(self.tank, action="record a receipt against")
		if flt(self.dispatches_kl) > 0:
			assert_tank_available(self.tank, action="record a dispatch against")

	def calculate_closing_volume(self):
		self.closing_volume_kl = flt(
			flt(self.opening_volume_kl)
			+ flt(self.receipts_kl)
			- flt(self.dispatches_kl)
			+ flt(self.adjustments_kl),
			3,
		)

	def on_update(self):
		log_journey_step(self.journey_ref, "4. Inventory Position", self)
