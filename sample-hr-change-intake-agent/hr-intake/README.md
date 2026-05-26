# HR Change Intake & Policy Auditing Agent

An AI-assisted, premium agentic intake engine designed to orchestrate HR personnel changes (promotions, transfers, terminations, pay adjustments) for Store Leaders, enforce policy guidelines in real-time, and file structured review tickets.

Built with **Google Agent Development Kit (ADK)** and fully enabled for both **Agent-to-UI (A2UI)** and **Agent-to-Agent (A2A)** workflows.

---

## 🚀 Architecture & Capabilities

- **Interactive intake forms (A2UI):** Streams rich, structured UI elements (Cards, Columns, TextFields, ChoicePickers, Buttons) utilizing A2UI v0.9 specifications for a premium, interactive manager experience.
- **Unified directory pre-population:** Queries a mock Microsoft Entra ID and UKG Pro REST API MCP servers to instantly pre-populate current job profiles.
- **Real-time policy gatekeeping:** Performs immediate calculations (e.g., pay increase percentages exceeding 20%, backdated effective dates, and Job Code base threshold validations) and prompts managers for required justifications before submission.
- **Enterprise-ready Ticketing:** Supports dynamic toggling between offline mock simulations and **Google Cloud Application Integration Connectors** for Jira Service Management and Jira Cloud.
- **A2A Protocol Compliance:** Scaffolded using the `adk_a2a` template, exposing standardized endpoints for peer agents to invoke this reasoning engine programmatically.

---

## ⚙️ 1. Configuration Setup (`.env`)

The project utilizes a `.env` file to manage all local environment, python execution paths, and API configurations.

### A. Copy the Environment Template
Create your local `.env` file by copying the provided example template:

```bash
cp .env.example .env
```

### B. Edit the `.env` File
Open `.env` and configure the following variables to match your local environment and paths:

- **`GOOGLE_CLOUD_PROJECT`**: Set to your Google Cloud Project ID (e.g., `<your-project-id>`).
- **`MSFT_MCP_SERVER_PYTHON_PATH`**: The absolute path to the virtual environment python binary inside your `msft-mock-api-mcp` project folder.
- **`MSFT_MCP_SERVER_SCRIPT_PATH`**: The absolute path to the `mock_msft_mcp_server.py` script inside your `msft-mock-api-mcp/mcp` folder.
- **`UKG_MCP_SERVER_PYTHON_PATH`**: The absolute path to the virtual environment python binary inside your `ukg-mock-api-mcp` project folder.
- **`UKG_MCP_SERVER_SCRIPT_PATH`**: The absolute path to the `mock_ukg_mcp_server.py` script inside your `ukg-mock-api-mcp/mcp` folder.

*All other mock base URLs, authentication keys, and local endpoints are pre-configured and ready to run!*

---

## 💻 2. Local Development & Testing

To test the agent locally, you must run the mock Microsoft Graph REST API service in the background and launch the ADK local playground.

### A. Install Project Dependencies
On secure corporate environments, install all dependencies (including core and dev extras) using the authenticated registry bypass command:

```bash
# 1. Create the Python virtual environment
uv venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Generate access token
export ARTIFACT_REGISTRY_TOKEN=$(gcloud auth application-default print-access-token)

# 4. Run authenticated uv sync
UV_NO_CONFIG=1 \
UV_INDEX_URL=https://pypi.org/simple \
UV_EXTRA_INDEX_URL="https://oauth2accesstoken:${ARTIFACT_REGISTRY_TOKEN}@us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/" \
uv sync --all-groups --extra lint --extra eval --prerelease=allow
```

### B. Start the Mock Microsoft Graph REST Service
In a separate terminal, launch the mock Microsoft Graph API uvicorn server backed by BigQuery (disabling mTLS for corporate PTY compatibility):

```bash
cd ../msft-mock-api-mcp

# Launch the mock uvicorn server on port 8081
GOOGLE_API_USE_MTLS_ENDPOINT=never \
GOOGLE_API_USE_CLIENT_CERTIFICATE=false \
.venv/bin/uvicorn api.mock_msft_graph_api:app --host 127.0.0.1 --port 8081
```

### C. Run Verification and Formatting Checks
Ensure code styling and type safety are 100% correct:

```bash
# Auto-format code style
uv run ruff format .

# Auto-fix imports and linting issues
uv run ruff check . --fix

# Audits type safety parameters
uv run ty check .
```

### D. Execute the Evaluation Suite
Run the multi-turn promotion evalset to verify perfect 100% scoring matches:

```bash
export ARTIFACT_REGISTRY_TOKEN=$(gcloud auth application-default print-access-token)

UV_NO_CONFIG=1 \
UV_INDEX_URL=https://pypi.org/simple \
UV_EXTRA_INDEX_URL="https://oauth2accesstoken:${ARTIFACT_REGISTRY_TOKEN}@us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/" \
uv run adk eval ./app tests/eval/evalsets/hr_intake.evalset.json --config_file_path tests/eval/eval_config.json
```

### E. Start Local Interactive Web Playground
To test the agent interactively in your browser and inspect streamed A2UI components:

```bash
agents-cli playground
```

---

## 🚀 3. Deploying to Google Cloud Agent Engine

When you are ready to transition from local prototyping to a cloud-deployed reasoning engine service:

1. **Select your GCP Project:**
   ```bash
   gcloud config set project <your-project-id>
   ```
2. **Deploy to Agent Engine (Agent Runtime):**
   Run the CLI deploy directive to automatically compile, containerize, and upload the bundle:
   ```bash
   agents-cli deploy
   ```

---

## 🏢 4. Registering the Agent in a Gemini Enterprise App

Once the agent has been deployed to Agent Engine:

1. **Publish the Agent:**
   Execute the CLI publish command to register the reasoning engine directly with your Gemini Enterprise subscription:
   ```bash
   agents-cli publish gemini-enterprise
   ```
2. **Access via Google Cloud Console:**
   - Navigate to the **GCP Console** -> **Agent Engine** (or **Reasoning Engine**).
   - Open your deployed `hr_intake_agent` instance to verify that the cloud endpoints are successfully active.
   - Link the deployed agent's service name directly under your target **Gemini Enterprise App** panel to enable conversational access for users.

---

## 🧪 5. Testing in Gemini Enterprise (Sample Prompts)

Once active inside your Gemini Enterprise App interface, test the agent's full dual-MCP directories, policy calculations, justification requirements, A2UI forms, and JIRA dispatches using these **Sample Prompts**:

### Prompt 1: Initiating Promotion & Directory Pre-population
*   **User Input:**
    ```text
    I want to promote employee EMP1001.
    ```
*   **Expected Response:**
    The agent will fetch Alex Mercer's profile (displayName, mail, store Location) concurrently from the Microsoft Graph MCP, and his salary/grade from the UKG Compensation MCP. It will display a beautiful, pre-populated A2UI current details card, followed by a promotion input form asking for the target role (ASL01/SL01), proposed pay rate, and effective date.

### Prompt 2: Testing High Pay Increase Policy Thresholds
*   **User Input:**
    *(Fill out the A2UI Form or type:)*
    ```text
    Promote Alex Mercer to Store Leader (SL01) at $22.50/hr starting June 1st, 2026.
    ```
*   **Expected Response:**
    The agent calculates that raising Alex's pay from $16.50/hr to $22.50/hr is a **36.36% increase**, exceeding the **20% company threshold**. It will trigger the **⚠️ High Pay Increase Threshold Policy Flag**, render a warning card explaining the rule, and serve an interactive multi-line TextField asking for a business justification.

### Prompt 3: Testing Backdated Effective Date Policy Gates
*   **User Input:**
    ```text
    Promote Alex Mercer to Store Leader (SL01) at $24.00/hr starting May 10th, 2026.
    ```
*   **Expected Response:**
    The agent audits the inputs and triggers **two simultaneous policy gates**:
    1. **Backdated Date Gate:** The effective date is in the past relative to today's system date (May 21st, 2026). It flags this as a **⚠️ Backdated Effective Date Policy Flag**.
    2. **High Pay Increase Gate:** The $24.00/hr rate represents a **45.45% increase** (exceeding 20%).
    It will request justifications for both flags using interactive input fields.

### Prompt 4: Providing Justification & Final Ticket Submission
*   **User Input:**
    ```text
    Justification is that Alex Mercer has been performing stellar work as SGA and is fully ready to lead Store 4550. Submit the request, and notify me via SMS at +1-555-019-1002
    ```
*   **Expected Response:**
    The agent will compile the inputs, successfully create a ticket in the Jira HR Review Queue (via Integration Connectors or simulated tool), dispatch an SMS notification message confirming the tickey key, and render a clean, structured **HR Reviewer Summary Card** listing the justification and verified policy flags.
