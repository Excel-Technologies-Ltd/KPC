# Copyright (c) 2026, ArcApps and contributors
# For license information, please see license.txt
"""Create the Workflow that gates AI Recommendation approval.

Pending Approval -> Approved / Rejected, restricted to the Maintenance
Manager role - the brief is explicit that this role "exclusively approves
AI Recommendations and Work Orders" (Work Order approval is handled by
submit permissions on Maintenance Work Order instead, since that doctype's
lifecycle is a simple approve/don't-approve rather than a branching state
machine).
"""

import frappe

WORKFLOW_STATES = [
	("Pending Approval", "Warning"),
	("Approved", "Success"),
	("Rejected", "Danger"),
]

WORKFLOW_ACTIONS = ["Approve Recommendation", "Reject Recommendation"]


def execute():
	create_workflow_states()
	create_workflow_actions()
	create_ai_recommendation_workflow()


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


def create_ai_recommendation_workflow():
	if frappe.db.exists("Workflow", "AI Recommendation Workflow"):
		return

	workflow = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": "AI Recommendation Workflow",
			"document_type": "AI Recommendation",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{"state": "Pending Approval", "doc_status": "0", "allow_edit": "Maintenance Manager"},
				{"state": "Approved", "doc_status": "0", "allow_edit": "Maintenance Manager"},
				{"state": "Rejected", "doc_status": "0", "allow_edit": "Maintenance Manager"},
			],
			"transitions": [
				{
					"state": "Pending Approval",
					"action": "Approve Recommendation",
					"next_state": "Approved",
					"allowed": "Maintenance Manager",
				},
				{
					"state": "Pending Approval",
					"action": "Reject Recommendation",
					"next_state": "Rejected",
					"allowed": "Maintenance Manager",
				},
			],
		}
	)
	workflow.insert(ignore_permissions=True)
