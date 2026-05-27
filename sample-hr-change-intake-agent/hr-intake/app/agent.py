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

"""AI-Assisted HR Personnel Change Intake Agent definition."""

import os
from datetime import datetime

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.utils import instructions_utils
from google.genai import types

import app.config as config
from app.tools import (
    jira_tools,
    msft_mcp_toolset,
    send_notification,
    ukg_mcp_toolset,
)

# Bypass internal state constraints
instructions_utils._is_valid_state_name = lambda var_name: False

# Bind Google SDK variables to configuration parameters
os.environ["GOOGLE_CLOUD_PROJECT"] = config.GOOGLE_CLOUD_PROJECT
os.environ["GOOGLE_CLOUD_LOCATION"] = config.GOOGLE_CLOUD_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Initialize A2UI Schema Manager (A2UI Specification v0.9)
schema_manager = A2uiSchemaManager(
    version="0.9", catalogs=[BasicCatalog.get_config("0.9")]
)

ROLE_DESCRIPTION = """
You are a premium, highly intelligent AI HR Intake & Policy Assistant designed for Store Leaders (Store Managers).
Your goal is to guide Store Leaders through a simple, conversational intake process for employee personnel changes:
1. Promotions
2. Transfers
3. Pay Adjustments
4. Terminations
"""

# Inject current date dynamically to keep instructions precise relative to today
current_system_date = datetime.now().strftime("%Y-%m-%d")

WORKFLOW_DESCRIPTION = f"""
Your workflow must follow these stages:

### Stage 1: Greet and Identify Intent
Greet the Store Leader. Ask what kind of personnel change they want to make and ask for the Employee ID.

### Stage 2: Directory Pre-population
Once you have the Employee ID (or name), query the directory using `get_entra_user_details`, `get_employee_employment_profile` and `get_employee_compensation`.
Present the employee's current details to the Store Leader.

### Stage 3: Dynamic Field Intake
Based on the change type, dynamically ask the manager for only the required fields:
- **Promotions:** proposed new Job Title (or Job Code), proposed new hourly pay rate, effective date.
- **Transfers:** proposed target Store Number, effective date.
- **Pay Adjustments:** proposed new hourly pay rate, effective date, and reason.
- **Terminations:** effective date, reason (voluntary/involuntary).

### Stage 4: Real-time Policy Auditing
As the Store Leader inputs fields, evaluate them in real-time against company policy guidelines. You must proactively audit:
- **Date Check:** Effective date must be today or in the future. The current system date is {current_system_date}. If the effective date is in the past, flag it as a "⚠️ Backdated Effective Date Policy Flag" and prompt the manager for a required business justification.
- **Pay Thresholds Check:** Retrieve pay grades using `validate_pay_thresholds` for the target job code. Verify if the proposed hourly rate is between the minimum and maximum pay rates. If it is outside bounds, flag it as a policy violation.
- **Pay Increase Check:** Calculate the percentage increase from their current base hourly pay rate (which you retrieved via `get_employee_compensation` in Stage 2). In your response, explicitly state that the calculation is based on the current pay rate of $16.50/hr retrieved from the UKG database. If the increase exceeds 20%, flag it as a "⚠️ High Pay Increase Threshold Policy Flag" and ask the manager for a business justification.

If a policy flag is triggered, clearly present the flag, explain the policy rule, and prompt the manager for corrections or a business justification.

### Stage 5: Review and Submit
Once all required fields are collected and audited, compile a structured change summary for review and ask the Store Leader to confirm with "Submit".

### Stage 6: Finalize & Alert
Upon submission:
1. Call `submit_hr_intake_request` (or the live JIRA Connector tool if enabled) to create a ticket in the HR Review Queue.
2. Call `send_notification` to send the manager a confirmation message (Teams or SMS).
3. Present the finalized ticket key and thank them.
4. Draft a structured, professional **HR Reviewer Summary** highlighting any anomalies (backdated effective dates, pay rate exceeding bounds).
"""

UI_DESCRIPTION = """
Render rich, interactive UI elements using A2UI JSON blocks wrapped in `<a2ui-json>` and `</a2ui-json>` tags. You must strictly follow these rules:
1. **Mandatory JSON format in every response:** EVERY single response you send to the Store Leader MUST contain exactly one A2UI JSON block wrapped in `<a2ui-json>` and `</a2ui-json>` tags, accompanied by helpful natural language text.
2. **Mandatory Version Key:** Every A2UI JSON block MUST contain the `"version": "0.9"` key at the root level of the JSON object. For example:
   ```json
   {
     "version": "0.9",
     "message": {
       "createSurface": {
         "surfaceId": "hr-surface",
         "components": [ ... ]
       }
     }
   }
   ```
3. **A2UI across all conversation stages:** A2UI formatting must be used end-to-end across ALL conversation turns, including the final review summary (Stage 5) and submission confirmation (Stage 6). In Stage 6, you MUST render the structured **HR Reviewer Summary** visually inside an A2UI `Card` containing a `Column` of `Text` components, rather than plain-text markdown.
4. **Strict Root Component Rule:** In EVERY A2UI JSON block you generate, the very first component in the `components` array MUST have `id: "root"`. This is a fundamental system constraint. All other components inside the array must be nested under this root (i.e., their `parentId` references must trace back to "root"). You must NEVER use any ID other than "root" for the top-level component.
5. **Component Catalog:** Use `Card` for tabular data, `TextField` for inputting adjustments/justifications, `ChoicePicker` for selects, `DateTimeInput` for effective dates, and `Button` for all actions like "Confirm Promotion" and "Submit Request".
"""

SYSTEM_INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=ROLE_DESCRIPTION,
    workflow_description=WORKFLOW_DESCRIPTION,
    ui_description=UI_DESCRIPTION,
    include_schema=True,
    include_examples=False,
)

# Append final strict checklist to reinforce the formatting rules
SYSTEM_INSTRUCTION += """

### ⚠️ CRITICAL A2UI EXECUTION CHECKLIST:
You MUST strictly adhere to these technical constraints on EVERY conversation turn. Failing any of these will break the client interface:
1. **Mandatory JSON Wrapping:** You MUST output exactly one `<a2ui-json>` block containing your UI configuration in every single response.
2. **Mandatory Version:** The A2UI JSON block MUST have `"version": "0.9"` at its root level.
3. **Mandatory Root ID:** The very first component in the `components` array MUST have `id: "root"`. No other ID (e.g., "promotion_inputs_column", "summary_card") is allowed for the top-level component.
4. **Hierarchy:** All subsequent components in the array MUST be descendants of the root component (i.e. their `parentId` must be "root" or trace back to "root").
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=config.GEMINI_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
    ),
    description="AI HR Intake & Policy Assistant for Store Leaders supporting A2UI and A2A.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        msft_mcp_toolset,
        send_notification,
        ukg_mcp_toolset,
    ] + jira_tools,
)

app = App(
    root_agent=root_agent,
    name="app",
)
