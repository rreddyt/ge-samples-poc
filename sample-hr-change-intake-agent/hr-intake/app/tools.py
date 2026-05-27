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

"""Custom tools and MCP toolsets for the AI-Assisted HR Personnel Change Intake Agent."""

import os
import uuid
from typing import Any

from google.adk.tools.application_integration_tool.application_integration_toolset import (
    ApplicationIntegrationToolset,
)
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

import app.config as config

# Resolve paths relative to this script's parent directory
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_path(path_str: str) -> str:
    """Resolves a path. If it is relative, resolves it relative to the agent root folder."""
    if not os.path.isabs(path_str):
        return os.path.normpath(os.path.join(AGENT_DIR, path_str))
    return path_str


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


# =====================================================================
# MCP Server Toolsets and Connector Toolsets Initialization
# =====================================================================

# Dynamic JIRA tools configuration
if config.USE_JIRA_INTEGRATION_CONNECTOR:
    jira_create_tool = ApplicationIntegrationToolset(
        project=config.GOOGLE_CLOUD_PROJECT,
        location=config.GOOGLE_CLOUD_REGION,
        connection=config.JIRA_CONNECTION_NAME,
        actions=["create_issue"],
        tool_name_prefix="jira_create_issue",
        tool_instructions="Use this tool to create intake tickets in Jira Service Management / Jira Cloud.",
    )
    jira_get_tool = ApplicationIntegrationToolset(
        project=config.GOOGLE_CLOUD_PROJECT,
        location=config.GOOGLE_CLOUD_REGION,
        connection=config.JIRA_CONNECTION_NAME,
        actions=["get_issue"],
        tool_name_prefix="jira_get_issue",
        tool_instructions="Use this tool to retrieve intake tickets in Jira Service Management / Jira Cloud.",
    )
    jira_tools = [jira_create_tool, jira_get_tool]
else:
    jira_tools = [submit_hr_intake_request]

# Dynamic Microsoft Graph MCP Toolset setup
if config.MSFT_MCP_SERVER_URL:
    msft_mcp_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=config.MSFT_MCP_SERVER_URL
        )
    )
else:
    msft_python_path = resolve_path(config.MSFT_MCP_SERVER_PYTHON_PATH)
    msft_script_path = resolve_path(config.MSFT_MCP_SERVER_SCRIPT_PATH)
    msft_mcp_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=msft_python_path,
                args=[msft_script_path],
                env={
                    "MSFT_API_BASE_URL": "http://127.0.0.1:8081",
                    "MSFT_API_KEY": "mock-auth-token-123",
                    "GOOGLE_CLOUD_PROJECT": config.GOOGLE_CLOUD_PROJECT,
                    "GOOGLE_API_USE_MTLS_ENDPOINT": "never",
                    "GOOGLE_API_USE_CLIENT_CERTIFICATE": "false",
                },
            ),
            timeout=30.0,
        )
    )

# Dynamic UKG MCP Toolset setup
if config.UKG_MCP_SERVER_URL:
    ukg_mcp_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=config.UKG_MCP_SERVER_URL
        )
    )
else:
    ukg_python_path = resolve_path(config.UKG_MCP_SERVER_PYTHON_PATH)
    ukg_script_path = resolve_path(config.UKG_MCP_SERVER_SCRIPT_PATH)
    ukg_mcp_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=ukg_python_path,
                args=[ukg_script_path],
                env={
                    "UKG_API_BASE_URL": "http://127.0.0.1:8080",
                    "UKG_API_KEY": "mock-auth-token-123",
                    "GOOGLE_CLOUD_PROJECT": config.GOOGLE_CLOUD_PROJECT,
                    "GOOGLE_API_USE_MTLS_ENDPOINT": "never",
                    "GOOGLE_API_USE_CLIENT_CERTIFICATE": "false",
                },
            ),
            timeout=30.0,
        )
    )
