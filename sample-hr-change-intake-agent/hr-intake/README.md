# HR Change Intake & Policy Auditing Agent

An AI-assisted, premium agentic intake engine designed to orchestrate HR personnel changes (promotions, transfers, terminations, pay adjustments) for Retail Store Leaders, enforce company policy guidelines in real-time, and file structured tickets for HR to review.

Built with **Google Agent Development Kit (ADK)**, and fully deployable to the **Gemini Enterprise Agent Platform Runtime (Agent Engine)** and compatible to be linked to **Gemini Enterprise Apps**.

---

## 🚀 1. Architecture & Capabilities

- **Interactive intake forms (A2UI):** Streams rich, structured UI elements (Cards, Columns, TextFields, ChoicePickers, Buttons) utilizing A2UI v0.9 specifications for a premium, interactive manager experience.
- **Unified directory pre-population:** Queries a mock Microsoft Entra ID and UKG Pro REST API MCP servers to instantly pre-populate current job profiles.
- **Real-time policy gatekeeping:** Performs immediate calculations (e.g., pay increase percentages exceeding 20%, backdated effective dates, and Job Code base threshold validations) and prompts managers for required justifications before submission.
- **Enterprise-ready Ticketing:** Supports dynamic toggling between offline mock simulations and **Google Cloud Application Integration Connectors** for Jira Service Management and Jira Cloud.
- **ADK Framework Compliance:** Standardized endpoints matching standard Vertex AI and Gemini Enterprise orchestrator requirements perfectly.

---

## 📋 2. Deployment Prerequisites

Before deploying this agent to **Agent Engine (Agent Runtime)**, ensure the following dependencies are set up:

### A. Mock MCP Servers
1. Deploy the mock Microsoft Graph and UKG MCP servers (e.g., to **Cloud Run**):
   - For instructions on configuring and deploying the Entra ID mock directory, see the [Microsoft Graph Mock MCP README](../../msft-mock-api-mcp/README.md).
   - For instructions on configuring and deploying the employee compensation details, see the [UKG Mock MCP README](../../ukg-mock-api-mcp/README.md).
2. Note their **Streamable HTTP endpoints** (usually ending in `/mcp`, such as `https://msft-graph-mcp-abc123-uc.a.run.app/mcp`).

### B. GCP Integration Connectors
1. Setup and provision the **Jira Service Management Connector** in GCP Integration Connectors:
   - For official instructions on provisioning and configuring the connector resource, see the [Jira Service Management Connector documentation](https://docs.cloud.google.com/integration-connectors/docs/connectors/jiraservicemanagement/configure#configure-the-connector).
2. Note the connector's resource name (e.g., `sample-jsm-conn`).

---

## ⚙️ 3. Configuration Setup (`.env`)

The project uses environment variables to manage local fallback stdio paths, live remote Cloud Run MCP URLs, and project settings.

### A. Copy the Environment Template
Create your local `.env` file by copying the provided example template:
```bash
cp .env.example .env
```

### B. Edit the `.env` File
Open `.env` and configure the following variables:

```ini
# ☁️ Google Cloud Platform Core Settings
GOOGLE_CLOUD_PROJECT=<your-gcp-project-id>
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_CLOUD_LOCATION=us-central1

# 🎫 Jira Connection Configuration (Mock/Local by default, set to true for connector)
USE_JIRA_INTEGRATION_CONNECTOR=true
JIRA_CONNECTION_NAME=<your-jsm-connector-name>

# 🏢 Microsoft Graph (Entra ID) Remote MCP Server URL (Streamable HTTP /mcp)
MSFT_MCP_SERVER_URL=https://<your-msft-graph-mcp-run-url>/mcp

# 🇬🇧 UKG (Ultimate Kronos Group) Remote MCP Server URL (Streamable HTTP /mcp)
UKG_MCP_SERVER_URL=https://<your-ukg-mcp-run-url>/mcp

# =====================================================================
# Local Fallback configurations (Only used if URL variables above are empty)
# =====================================================================
MSFT_MCP_SERVER_PYTHON_PATH=../../msft-mock-api-mcp/.venv/bin/python
MSFT_MCP_SERVER_SCRIPT_PATH=../../msft-mock-api-mcp/mcp/mock_msft_mcp_server.py
UKG_MCP_SERVER_PYTHON_PATH=../../ukg-mock-api-mcp/.venv/bin/python
UKG_MCP_SERVER_SCRIPT_PATH=../../ukg-mock-api-mcp/mcp/mock_ukg_mcp_server.py
```

---

## 💻 4. Local Development & Testing

Test your agent locally inside the **Agent Engine Web Playground** to visually verify the streamed A2UI component rendering:

### A. Install Project Dependencies
Install all dependencies (including core and dev groups) using `uv`:
```bash
# 1. Create the Python virtual environment
uv venv --python 3.12

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Run authenticated uv sync
uv sync --all-groups --extra lint --extra eval --prerelease=allow
```

### B. Execute the Validation Checks
Ensure styling, type safety, and unit/integration tests are 100% correct:
```bash
# Run type safety checks
uv run ty check .

# Run complete unit and integration test suite
uv run pytest tests/integration/test_agent.py
```

### C. Start Local Interactive Web Playground
Launch the ADK web playground. Because we've populated `.env` with your live remote Cloud Run MCP URLs, it will connect to them automatically!
```bash
GOOGLE_API_USE_MTLS_ENDPOINT=never GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli playground
```
*Navigate to `http://127.0.0.1:8080` in your browser and click **New Session** to begin testing.*

---

## 🚀 5. Deploying to Google Cloud Agent Engine

When you are ready to deploy your agent to **Agent Engine (Agent Runtime)** as a standard, secure Reasoning Engine:

### A. One-time IAM Permission Setup
Your Reasoning Engine runs under the Google-managed Vertex AI Service Agent (`service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com`). To allow the agent to access your Integration Connectors (like `sample-jsm-conn`), you must grant it Connectors Admin rights:

```bash
# Replace <your-gcp-project-id> and <your-gcp-project-number> with your values
gcloud projects add-iam-policy-binding <your-gcp-project-id> \
  --member="serviceAccount:service-<your-gcp-project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/connectors.admin" \
  --condition=None
```

### B. Deploy to Agent Engine
Run the deploy CLI command. The deployment is fully parameterized and will package your source files, synchronize dependencies, and register the Reasoning Engine dynamically in `us-central1`:

```bash
GOOGLE_API_USE_MTLS_ENDPOINT=never GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy \
  --project <your-gcp-project-id> \
  --region us-central1 \
  --no-confirm-project \
  --update-env-vars "USE_JIRA_INTEGRATION_CONNECTOR=true,JIRA_CONNECTION_NAME=<your-jsm-connector-name>,MSFT_MCP_SERVER_URL=https://<your-msft-graph-mcp-run-url>/mcp,UKG_MCP_SERVER_URL=https://<your-ukg-mcp-run-url>/mcp,GOOGLE_CLOUD_REGION=us-central1"
```

Once deployment completes, it will output your live **Agent Runtime ID** (e.g. `projects/<your-gcp-project-number>/locations/us-central1/reasoningEngines/<engine-id>`).

---

## 🏢 6. Linking the Agent to your Gemini Enterprise App

Once deployed, link the agent to your target Gemini Enterprise application using the Google Cloud Console:

1.  **Open the GCP Console**: Navigate to the [GCP Console](https://console.cloud.google.com/) and select **`<your-gcp-project-id>`**.
2.  **Navigate to Agent Builder**: Search for **"Agent Builder"** in the top search bar and click on **Apps** in the left sidebar.
3.  **Select your App**: Click on the name of the Gemini App you want to connect (e.g., `Gamestop Store Agent`).
4.  **Create / Add Agent**:
    *   Click on the **Agents** tab in the sidebar and click **+ Add agent** (or **Create agent**).
    *   **Step 1: Authorizations**: Click **Skip** (since the agent handles credentials at the system level using Service Accounts).
    *   **Step 2: Configuration**:
        *   **Agent name**: `HR Change Intake Agent`
        *   **Describe your agent**: `An AI HR Intake & Policy Assistant designed to guide store leaders and managers through employee personnel changes (promotions, transfers, pay adjustments, and terminations), enforce company policy guidelines in real-time, and file structured review tickets.`
        *   **Agent Engine reasoning engine**: Enter the deployed Reasoning Engine ID (e.g. `projects/<your-gcp-project-number>/locations/us-central1/reasoningEngines/<engine-id>`).
        *   **Agent invocation specification**: `Use this agent when a user wants to initiate, manage, calculate, or submit any HR personnel changes, employee promotions, hourly pay rate adjustments, store transfers, or terminations. Do not invoke this agent for non-HR general support queries.`
        *   **Invocation Mode**: `Automatic`
    *   Click **Create** to finish!

---

## 🧪 7. Conversational Test Suite (Suggested Prompts)

Start a **New Chat** in your Gemini Enterprise App to test the multi-turn workflow:

-   **Turn 1 (Pre-populate Profile):**
    *   *User prompt:* `I want to promote employee EMP1001.`
    *   *Expected Response:* Agent fetches Alex Mercer's Entra ID and UKG records, displays his current details card, and streams the promotion intake form.
-   **Turn 2 (Pay Increase Threshold Check):**
    *   *User prompt:* `Promote Alex Mercer to Store Leader (SL01) at $22.50/hr starting June 1st, 2026.`
    *   *Expected Response:* Agent calculates a **36.36% increase** (exceeding 20%), flags the **⚠️ High Pay Increase Policy Flag**, and prompts you with an input text field for business justification.
-   **Turn 3 (Backdated Date Gate Check):**
    *   *User prompt:* `Promote Alex Mercer to Store Leader (SL01) at $24.00/hr starting May 10th, 2026.`
    *   *Expected Response:* Agent flags both **⚠️ Backdated Effective Date Policy Flag** (since May 10th is in the past) and **⚠️ High Pay Increase Gate**, asking for justifications for both.
-   **Turn 4 (Submit to JIRA):**
    *   *User prompt:* `Justification is that Alex Mercer has been performing stellar work as SGA and is fully ready to lead Store 4550. Submit the request, and notify me via SMS at +1-555-019-1002`
    *   *Expected Response:* Agent creates a ticket in the Jira HR Review Queue via the Integration Connector, dispatches the SMS message, and renders the visual HR Reviewer Summary Card!
