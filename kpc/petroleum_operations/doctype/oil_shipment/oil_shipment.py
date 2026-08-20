# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from kpc.petroleum_operations.utils import log_journey_step


class OilShipment(Document):
	def before_insert(self):
		self.create_journey()

	def validate(self):
		self.stamp_workflow_timestamps()

	def on_update(self):
		self.sync_journey_log()

	def create_journey(self):
		"""Every Oil Shipment is the origin of exactly one Golden Thread.
		The Journey is created here (before_insert) so journey_ref is
		guaranteed to exist the moment the Shipment first hits the database.
		"""
		if self.journey_ref:
			return

		journey = frappe.get_doc(
			{
				"doctype": "Journey",
				"status": "Active",
				"current_step": "1. Shipment",
				"product": self.product,
			}
		)
		journey.insert(ignore_permissions=True)
		self.journey_ref = journey.name

	def stamp_workflow_timestamps(self):
		if not self.has_value_changed("workflow_state"):
			return
		if self.workflow_state == "Vessel Arrived" and not self.ata:
			self.ata = now_datetime()
		if self.workflow_state == "Discharging" and not self.discharge_start:
			self.discharge_start = now_datetime()
		if self.workflow_state == "Received" and not self.discharge_end:
			self.discharge_end = now_datetime()

	def sync_journey_log(self):
		if not self.journey_ref:
			return
		# Backfill origin_shipment the first time (Journey was created
		# before this Shipment had a name).
		if not frappe.db.get_value("Journey", self.journey_ref, "origin_shipment"):
			frappe.db.set_value("Journey", self.journey_ref, "origin_shipment", self.name)
		if self.has_value_changed("workflow_state"):
			log_journey_step(self.journey_ref, "1. Shipment", self)

	def on_trash(self):
		frappe.throw(
			_("Oil Shipment {0} cannot be deleted: it is the origin of Golden Thread {1}.").format(
				self.name, self.journey_ref
			)
		)
