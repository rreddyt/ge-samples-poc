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

"""Configuration variables for the HR Personnel Change Intake Agent."""

import os
import google.auth
from dotenv import load_dotenv

# Load environment variables from local .env file if present
load_dotenv()

# Google Cloud Core Configurations
_, default_project_id = google.auth.default()
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", default_project_id)
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Gemini Model Configurations
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "4096"))

# Jira Connector Configurations
USE_JIRA_INTEGRATION_CONNECTOR = (
    os.environ.get("USE_JIRA_INTEGRATION_CONNECTOR", "false").lower() == "true"
)
JIRA_CONNECTION_NAME = os.environ.get("JIRA_CONNECTION_NAME", "jira-connector")

# Remote MCP Configurations (Cloud Run / Production)
MSFT_MCP_SERVER_URL = os.environ.get("MSFT_MCP_SERVER_URL")
UKG_MCP_SERVER_URL = os.environ.get("UKG_MCP_SERVER_URL")

# Local Stdio MCP Configurations (Fallback for Local Stdio Development)
MSFT_MCP_SERVER_PYTHON_PATH = os.environ.get(
    "MSFT_MCP_SERVER_PYTHON_PATH",
    "../../msft-mock-api-mcp/.venv/bin/python"
)
MSFT_MCP_SERVER_SCRIPT_PATH = os.environ.get(
    "MSFT_MCP_SERVER_SCRIPT_PATH",
    "../../msft-mock-api-mcp/mcp/mock_msft_mcp_server.py"
)

UKG_MCP_SERVER_PYTHON_PATH = os.environ.get(
    "UKG_MCP_SERVER_PYTHON_PATH",
    "../../ukg-mock-api-mcp/.venv/bin/python"
)
UKG_MCP_SERVER_SCRIPT_PATH = os.environ.get(
    "UKG_MCP_SERVER_SCRIPT_PATH",
    "../../ukg-mock-api-mcp/mcp/mock_ukg_mcp_server.py"
)
