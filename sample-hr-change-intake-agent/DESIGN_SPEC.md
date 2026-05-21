# DESIGN_SPEC.md - AI-Assisted HR Personnel Change Intake Agent

## Overview
The **AI-Assisted HR Personnel Change Intake Agent** is built to streamline and automate personnel changes (promotions, transfers, terminations, and pay adjustments) initiated by Store Managers (Store Leaders). It authenticates leaders, pre-populates employee directory data using Microsoft Entra ID, performs real-time HR policy checks, integrates with UKG Pro REST API / MCP, and drafts detailed summaries for HR Administrators / HR Reviewers.

The agent uses:
- Conversational intake to dynamically request only fields needed for specific change types.
- Entra ID directory query via Graph API.
- UKG Pro MCP tool for employment profile, compensation details, and pay rate validations.
- Policy gatekeeping to prevent incorrect dates, backdated events, or out-of-bounds pay rates.
- Multi-channel alerting (Teams/SMS/Email) to notify managers of progress.
- Summaries drafted for HR review.

## Example Use Cases
1. **Promotion with Pay Adjustment:**
   - **Input:** "I want to promote employee EMP1001 to Store Manager (SL01) and set hourly pay rate to $22.50 starting June 1st, 2026."
   - **Agent Action:**
     1. Queries Entra ID / UKG profile to fetch `EMP1001` current details (Senior Game Advisor, Store 4550, current pay $16.50/hr).
     2. Validates the target job code `SL01` (Store Leader) pay grades (e.g. Min: $20.00, Max: $25.00).
     3. Checks if $22.50/hr is within policy bounds (Yes, complies).
     4. Prompts manager to confirm details.
     5. Generates submission summary and inserts into review queue.
   - **Output:** "The promotion request for EMP1001 to Store Leader at $22.50/hr starting 2026-06-01 has been drafted and submitted. No policy violations were flagged."

2. **Termination (Policy Conflict):**
   - **Input:** "I need to terminate Employee ID EMP1002 starting May 10th, 2026."
   - **Agent Action:**
     1. Queries employee details for `EMP1002`.
     2. Checks the effective date (May 10th, 2026) against today's date (May 21st, 2026).
     3. Flags that the termination date is set in the past (backdated).
     4. Prompts the store leader to correct or provide a justification.
   - **Output:** "❌ Effective termination date (2026-05-10) is in the past. Standard HR policy requires future-dated or current-day termination processing. Please provide a valid reason or update the effective date."

## Tools Required

### 1. Entra ID / Microsoft Graph API Tools
- **`get_entra_user_details(employee_id)`**: Query employee directory details (Name, Supervisor, Current Title, Store Location, Email/Phone).

### 2. UKG Pro MCP Tools
- **`get_employee_employment_profile(employee_id)`**: Fetch active job title, primary job code, manager, store number.
- **`get_employee_compensation(employee_id)`**: Fetch exact base hourly pay rate, pay grade level, pay frequency.
- **`validate_pay_thresholds(job_code)`**: Fetch standard min/max pay ranges for a job code.
- **`get_valid_jobs_and_locations()`**: Fetch lists of active job profiles and store location codes.

### 3. Policy Check Logic Tools (Built-in Python Functions or Agent tools)
- **`check_policy_rules(change_type, details)`**: Check for backdated effective dates, pay rate threshold compliance (e.g. max pay rate, or percentage pay increase exceeding X% threshold).

### 4. Jira / Atlassian Service Management Tools
- **`create_hr_intake_ticket(summary, details)`**: Creates the Jira ticket acting as HR's intake / review queue.

### 5. Notification Tools
- **`send_notification(manager_channel, message)`**: Send updates via MS Teams / SMS / Email to the Store Leader.

## Constraints & Safety Rules
- **Date Policies:** Effective dates must be today or in the future. Backdated actions are flagged and require mandatory reviewer approval + justification text.
- **Pay Rate Policies:** Pay rate must fall within the min/max range for the target Job Code (fetched via `validate_pay_thresholds`). If it exceeds, or if the increase is greater than a configurable threshold (e.g. 20%), a warning must be shown and require justification.
- **Privacy / Confidentiality:** Compensation details must only be discussed with the authenticated Store Leader.
- **Role Boundaries:** Store Leaders can only perform changes for employees in their own Store/Organization unit.

## Success Criteria
- Successful pre-population of Employee details in < 3 seconds.
- Accurate flagging of all backdated dates and out-of-bounds pay levels.
- Automated generation of plain-language briefing sheet / ticket for HR Reviewers.

## Reference Samples
- **`adk-ae-oauth`**: Standard OAuth flow and Agent Runtime deployment pattern.
- **` Genmedia for Commerce` / ` Genmedia`**: MCP tool integration model.
