# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Create the Workflow that gates Variance approval.

Pending Approval -> Approved / Rejected, restricted to the Scheduler &
Operations Controller role per the brief's RBAC table ("Variance approval").
"""

import frappe

WORKFLOW_ACTIONS = ["Approve Variance", "Reject Variance"]


def execute():
	create_workflow_actions()
	create_variance_workflow()


def create_workflow_actions():
	# Workflow States (Pending Approval/Approved/Rejected) already exist from
	# the AI Recommendation Workflow patch - only new Action labels are needed.
	for action in WORKFLOW_ACTIONS:
		if frappe.db.exists("Workflow Action Master", action):
			continue
		frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
			ignore_permissions=True
		)


def create_variance_workflow():
	if frappe.db.exists("Workflow", "Variance Workflow"):
		return

	workflow = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": "Variance Workflow",
			"document_type": "Variance",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{
					"state": "Pending Approval",
					"doc_status": "0",
					"allow_edit": "Scheduler & Operations Controller",
				},
				{"state": "Approved", "doc_status": "0", "allow_edit": "Scheduler & Operations Controller"},
				{"state": "Rejected", "doc_status": "0", "allow_edit": "Scheduler & Operations Controller"},
			],
			"transitions": [
				{
					"state": "Pending Approval",
					"action": "Approve Variance",
					"next_state": "Approved",
					"allowed": "Scheduler & Operations Controller",
				},
				{
					"state": "Pending Approval",
					"action": "Reject Variance",
					"next_state": "Rejected",
					"allowed": "Scheduler & Operations Controller",
				},
			],
		}
	)
	workflow.insert(ignore_permissions=True)
