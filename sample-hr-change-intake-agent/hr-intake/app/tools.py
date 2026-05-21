# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom tools for the AI-Assisted HR Personnel Change Intake Agent."""

import uuid
from typing import Any

# Custom tools for the AI-Assisted HR Personnel Change Intake Agent.


def submit_hr_intake_request(summary: str, details: dict[str, Any]) -> dict[str, Any]:
    """Simulates creating a personnel intake ticket in Jira Service Management (Atlassian) for the HR Review Queue.

    Call this tool when the Store Manager confirms and submits a completed personnel change request (promotion, transfer, pay adjustment, termination).

    Args:
        summary: A descriptive title/summary of the request (e.g., 'Promotion Request: Alex Mercer (EMP1001) to Store Leader').
        details: A dictionary containing all change parameters (e.g., jobTitle, jobCode, hourlyPayRate, effectiveDate, storeNumber, justification, policyFlags).

    Returns:
        A dictionary indicating success, including the created Jira Ticket Key (e.g. 'HR-12345') and Status.
    """
    ticket_key = f"HR-{uuid.uuid4().hex[:5].upper()}"
    return {
        "status": "success",
        "message": "Successfully created intake ticket in Jira Service Management.",
        "ticketKey": ticket_key,
        "queue": "HR Intake & Review Queue",
        "summary": summary,
        "details": details,
    }


def send_notification(
    recipient_phone_or_email: str, channel: str, message: str
) -> dict[str, Any]:
    """Simulates sending progress milestone notifications to the store manager or employee.

    Use this to notify managers via their preferred channel (Teams, SMS, or Email) of intake progress and ticketing milestones.

    Args:
        recipient_phone_or_email: The email address, phone number, or Teams identifier to send the message to.
        channel: The notification delivery channel. Allowed values: 'Teams', 'SMS', 'Email'.
        message: The plain-language notification message content.

    Returns:
        A dictionary indicating delivery status.
    """
    normalized_channel = channel.strip().capitalize()
    if normalized_channel not in ("Teams", "Sms", "Email"):
        return {
            "status": "error",
            "message": f"Invalid channel '{channel}'. Must be 'Teams', 'SMS', or 'Email'.",
        }

    return {
        "status": "success",
        "channel": normalized_channel,
        "recipient": recipient_phone_or_email,
        "delivered": True,
        "messageSnippet": message[:60] + "..." if len(message) > 60 else message,
    }
