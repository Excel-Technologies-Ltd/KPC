# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Create the Frappe Workflows that drive Oil Shipment and Quality Result.

- Oil Shipment: Draft -> Vessel Arrived -> Discharging -> Received
- Quality Result: Pending -> Accepted / Quarantined
"""

import frappe

WORKFLOW_STATES = [
	# style must be one of: "", Primary, Info, Success, Warning, Danger, Inverse
	("Draft", ""),
	("Vessel Arrived", "Info"),
	("Discharging", "Warning"),
	("Received", "Success"),
	("Cancelled", "Danger"),
	("Pending", "Warning"),
	("Accepted", "Success"),
	("Quarantined", "Danger"),
]

WORKFLOW_ACTIONS = [
	"Mark Vessel Arrived",
	"Start Discharging",
	"Confirm Received",
	"Cancel Shipment",
	"Accept",
	"Quarantine",
]


def execute():
	create_workflow_states()
	create_workflow_actions()
	create_oil_shipment_workflow()
	create_quality_result_workflow()


def create_workflow_states():
	for state, style in WORKFLOW_STATES:
		if frappe.db.exists("Workflow State", state):
			continue
		frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
			ignore_permissions=True
		)


def create_workflow_actions():
	for action in WORKFLOW_ACTIONS:
		if frappe.db.exists("Workflow Action Master", action):
			continue
		frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
			ignore_permissions=True
		)


def create_oil_shipment_workflow():
	if frappe.db.exists("Workflow", "Oil Shipment Workflow"):
		return

	workflow = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": "Oil Shipment Workflow",
			"document_type": "Oil Shipment",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			# Oil Shipment is not submittable (see oil_shipment.json): the whole
			# lifecycle - including the terminal "Received"/"Cancelled" states -
			# runs on doc_status "0" and is governed purely by workflow
			# permissions/transitions below.
			"states": [
				{"state": "Draft", "doc_status": "0", "allow_edit": "Terminal Operator"},
				{"state": "Vessel Arrived", "doc_status": "0", "allow_edit": "Terminal Operator"},
				{
					"state": "Discharging",
					"doc_status": "0",
					"allow_edit": "Scheduler & Operations Controller",
				},
				{"state": "Received", "doc_status": "0", "allow_edit": "Scheduler & Operations Controller"},
				{"state": "Cancelled", "doc_status": "0", "allow_edit": "Scheduler & Operations Controller"},
			],
			"transitions": [
				{
					"state": "Draft",
					"action": "Mark Vessel Arrived",
					"next_state": "Vessel Arrived",
					"allowed": "Terminal Operator",
				},
				{
					"state": "Vessel Arrived",
					"action": "Start Discharging",
					"next_state": "Discharging",
					"allowed": "Terminal Operator",
				},
				{
					"state": "Discharging",
					"action": "Confirm Received",
					"next_state": "Received",
					"allowed": "Scheduler & Operations Controller",
				},
				{
					"state": "Draft",
					"action": "Cancel Shipment",
					"next_state": "Cancelled",
					"allowed": "Scheduler & Operations Controller",
				},
			],
		}
	)
	workflow.insert(ignore_permissions=True)


def create_quality_result_workflow():
	if frappe.db.exists("Workflow", "Quality Result Workflow"):
		return

	workflow = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": "Quality Result Workflow",
			"document_type": "Quality Result",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{"state": "Pending", "doc_status": "0", "allow_edit": "Quality Analyst"},
				{"state": "Accepted", "doc_status": "0", "allow_edit": "Quality Manager"},
				{"state": "Quarantined", "doc_status": "0", "allow_edit": "Quality Manager"},
			],
			"transitions": [
				{
					"state": "Pending",
					"action": "Accept",
					"next_state": "Accepted",
					"allowed": "Quality Manager",
					"condition": "doc.overall_result == 'Pass'",
				},
				{
					"state": "Pending",
					"action": "Quarantine",
					"next_state": "Quarantined",
					"allowed": "Quality Manager",
				},
			],
		}
	)
	workflow.insert(ignore_permissions=True)
