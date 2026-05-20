# 🧰 UKG Pro (HR/Payroll) MCP Integration Server PoC

A complete Proof of Concept (PoC) demonstrating how to integrate a retail store HR and Compensation system (UKG Pro) with **Gemini Enterprise (Vertex AI Agent Builder)** using the **Model Context Protocol (MCP)**. 

This server runs on **Google Cloud Run**, is backed by a mock dataset in **Google BigQuery**, and exposes secure, real-time tool-calling capabilities to your Gemini Enterprise AI agents.

---

## 📂 1. PoC Project Structure

The project is organized as follows inside the `hr-intake-agent-poc/` folder:

```text
hr-intake-agent-poc/
├── README.md                  # This architecture and setup guide
├── Dockerfile                 # Unified container definition for Cloud Run
├── requirements.txt           # Locked Python dependencies
├── api/
│   ├── __init__.py
│   └── mock_ukg_api.py        # FastAPI mock UKG REST API backed by BigQuery
├── mcp/
│   ├── __init__.py
│   └── mock_ukg_mcp_server.py # FastMCP Server exposing tools via stdio/HTTP
└── scripts/
    ├── setup_bq_mock_data.py  # Automates BigQuery dataset and sample data setup
    ├── test_mcp_client.py     # Standalone Python client to test tools locally
    └── debug_mcp.py           # Python client printing detailed tool call traces
```

---

## 🗄️ 2. BigQuery Sample Data Setup

The mock UKG data is hosted directly in Google BigQuery. The schema represents employee personal details, compensation rates, corporate job profiles, and retail organizational levels.

### Schema & Sample Records

| Table Name | Key Fields | Sample Records / Mock Data |
| :--- | :--- | :--- |
| **`person_details`** | `employeeId`, `firstName`, `lastName`, `email` | `EMP1001` (Alex Mercer), `EMP1002` (Sarah Connor), `EMP1003` (David Miller) |
| **`employment_details`** | `employeeId`, `jobTitle`, `primaryJobCode`, `supervisorName`, `orgLevel` | `EMP1001` -> Senior Game Advisor (`SGA01`), supervisor `Sarah Connor`, store `4550` |
| **`compensation_details`** | `employeeId`, `hourlyPayRate`, `annualSalary`, `payFrequency`, `payGrade` | `EMP1001` -> **$16.50/hr** ($34,320/yr), hourly, **GRADE_B** |
| **`pay_grades`** | `jobCode`, `payGrade`, `minimumPayRate`, `maximumPayRate` | `GA01` (Game Advisor) -> Min: **$13.00**, Max: **$15.50** |
| **`job_profiles`** | `jobCode`, `jobTitle`, `isActive` | `GA01` (Game Advisor), `SGA01` (Senior Game Advisor), `SL01` (Store Leader) |
| **`org_levels`** | `orgLevel` (Store #), `storeName`, `isActive` | `4550` (GameStop - Austin Central), `1024` (GameStop - Dallas North) |

### Automating Creation
You can regenerate the entire dataset, tables, and sample rows by executing the Python script. It automatically honors the BQ_DATASET environment variable if defined:
```bash
source .venv/bin/activate
GOOGLE_API_USE_MTLS_ENDPOINT=never GOOGLE_API_USE_CLIENT_CERTIFICATE=false \
BQ_DATASET="vr-payg-nonprod.ukg_mock_data" \
python3 scripts/setup_bq_mock_data.py
```

---

## 🌐 3. FastAPI Mock UKG REST API

The file **`api/mock_ukg_api.py`** implements a standard, read-only FastAPI application that matches UKG Pro REST endpoints, querying BigQuery in the background.

### 💡 Key Design Implementation: Thread Safety
In multi-threaded environments like FastAPI/Uvicorn, sharing a single `bigquery.Client()` object at the module level causes concurrent request conflicts and timeouts on Cloud Run. 
To prevent this, **the BigQuery client is instantiated dynamically inside the `run_query` scope for every request**:

```python
def run_query(query: str, parameters: list, fetch_one: bool = False):
    # Instantiated inside the function to ensure thread-safe execution
    bq_client = bigquery.Client()
    job_config = bigquery.QueryJobConfig(query_parameters=parameters)
    query_job = bq_client.query(query, job_config=job_config)
    return [dict(row) for row in query_job]
```

---

## 🧰 4. The FastMCP Server

The file **`mcp/mock_ukg_mcp_server.py`** implements the Model Context Protocol (MCP) server.

### Exposes 4 Tools:
1. **`get_employee_employment_profile(employee_id)`**: Retrieves current job title, primary job code, manager, and store number.
2. **`get_employee_compensation(employee_id)`**: Retrieves exact hourly base rate, frequency, and pay grade.
3. **`validate_pay_thresholds(job_code)`**: Retrieves min and max salary bounding ranges configured for a job code.
4. **`get_valid_jobs_and_locations()`**: Gathers active corporate Job Profiles and organizational store levels concurrently.

### 💡 Key Design: Dual-Transport Architecture
The server automatically detects its execution environment and toggles between:
1. **`stdio` transport**: Used for quick local testing and standard CLI/MCP Inspector integrations.
2. **`streamable-http` (Direct HTTP POST) transport**: Mounted explicitly at the **`/mcp`** route for stateless Cloud Run container deployments to connect to Gemini Enterprise.

```python
if __name__ == "__main__":
    import uvicorn
    
    # Detect serverless environment or explicit transport flags
    if os.environ.get("PORT") or os.environ.get("TRANSPORT") in ("sse", "http", "streamable-http"):
        port = int(os.environ.get("PORT", 8080))
        # Serves direct HTTP POST requests at the /mcp route
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
    else:
        # Standard stdio fallback for local CLI inspection
        mcp.run(transport="stdio")
```

---

## 🚀 5. Cloud Build & Deployment Instructions

Both services run from the same container image `ukg-mcp-poc-core:latest` but start with different execution commands. 

We use an `env.yaml` file to securely manage all project configurations and avoid hardcoding parameters in shell commands.

### Step 1: Create the `env.yaml` File
Create a file named `env.yaml` in the `hr-intake-agent-poc/` root directory with placeholders:

```yaml
# env.yaml - Unified Deployment Configurations
GOOGLE_CLOUD_PROJECT: "vr-payg-nonprod"
BQ_DATASET: "vr-payg-nonprod.ukg_mock_data"
UKG_API_BASE_URL: "https://mock-ukg-rest-api-placeholder"
UKG_API_KEY: "mock-auth-token-123"
```

### Step 2: Load Project ID and Build the Image
Extract the project ID from `env.yaml` and build the container image via Google Cloud Build:
```bash
# Extract project ID from env.yaml
export PROJECT_ID=$(grep "GOOGLE_CLOUD_PROJECT" env.yaml | awk -F'"' '{print $2}')

# Build and register the image
gcloud builds submit --tag gcr.io/$PROJECT_ID/ukg-mcp-poc-core:latest
```

### Step 3: Deploy the Mock UKG REST API
Deploy the REST API service to Cloud Run, sourcing the configurations directly from `env.yaml`:
```bash
gcloud run deploy mock-ukg-rest-api \
  --image gcr.io/$PROJECT_ID/ukg-mcp-poc-core:latest \
  --command="uvicorn" \
  --args="api.mock_ukg_api:app,--host,0.0.0.0,--port,8080" \
  --env-vars-file=env.yaml \
  --region=us-central1 \
  --allow-unauthenticated
```

### Step 4: Automatically Fetch the API URL & Update `env.yaml`
Instead of manually copying the generated Cloud Run URL of the REST API, **run this shell snippet to query the URL dynamically and update `env.yaml` programmatically**:
```bash
# 1. Query the dynamically generated Cloud Run URL
export MOCK_API_URL=$(gcloud run services describe mock-ukg-rest-api --region=us-central1 --format="value(status.url)")

# 2. Update the UKG_API_BASE_URL parameter inside env.yaml programmatically
sed -i "s|UKG_API_BASE_URL:.*|UKG_API_BASE_URL: \"$MOCK_API_URL\"|" env.yaml
```

### Step 5: Deploy the MCP Channel Server
Deploy the MCP tool server to Cloud Run. It will automatically use the dynamically updated `UKG_API_BASE_URL` from `env.yaml`:
```bash
gcloud run deploy ukg-mcp-channel \
  --image gcr.io/$PROJECT_ID/ukg-mcp-poc-core:latest \
  --command="python" \
  --args="mcp/mock_ukg_mcp_server.py" \
  --env-vars-file=env.yaml \
  --region=us-central1 \
  --allow-unauthenticated
```

### Step 6: Grant Discovery Engine Invoker Rights
Extract the project number from the project description and grant the Discovery Engine service account invoker rights:
```bash
# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant serviceAccount invoker rights
gcloud run services add-iam-policy-binding ukg-mcp-channel \
  --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.servicesInvoker" \
  --region=us-central1
```

---

## 🧠 6. Gemini Enterprise Custom MCP Configuration

To add your MCP server as a secure data store/tool in the **Gemini Enterprise (Vertex AI Agent Builder)** console:

1. Navigate to **Gemini Enterprise** -> **Data Stores** -> **Create Data Store**.
2. Select **Custom MCP**.
3. Fill out the configuration exactly as mapped in the table below:

### 📝 Step 1: Connection & Auth Settings

| Field Name | Exact Value to Enter | Description |
| :--- | :--- | :--- |
| **MCP Server URL \*** | `https://[YOUR_MCP_SERVER_URL]/mcp` | **Crucial:** Must include the `/mcp` path where FastMCP serves direct HTTP POSTs. |
| **Authorization URL \*** | `https://accounts.google.com/o/oauth2/v2/auth` | Google Accounts OAuth authorization endpoint. |
| **Authorization URL Parameters** | `&access_type=offline&prompt=consent` | Mandates refresh token exchange parameters. |
| **Token URL \*** | `https://oauth2.googleapis.com/token` | Google Accounts OAuth token exchange endpoint. |
| **Client ID \*** | `[YOUR_GOOGLE_CLIENT_ID]` | Deployed Google Client ID credentials. |
| **Client Secret \*** | `[YOUR_GOOGLE_CLIENT_SECRET]` | Deployed Google Client Secret credentials. |
| **Scopes** | `openid email profile` | Scopes requested during user sign-in. |

> 💡 **Important:** Click the **Login** button at the bottom of the form, complete the Google corporate accounts popup flow successfully, and verify you are logged in before clicking **Continue**.

### 📝 Step 2: Advanced Options (Orchestrator System Prompts)

*   **MCP Server Description:**
    ```text
    A secure, read-only HR and Compensation integration server for UKG Pro (formerly Ultimate Software). It provides real-time access to employee profiles, active job titles, compensation metrics, pay grades, and store location mappings. It enables the agent to query store employee details, validate salary ranges, and retrieve organizational metadata for a retail store network.
    ```
*   **MCP Agent Instructions:**
    ```text
    You are an expert HR assistant. Follow these guidelines when using the UKG MCP tools:
    1. To retrieve a store employee's current job title, primary job code, manager name, and active store location, invoke 'get_employee_employment_profile'.
    2. To inspect exact payroll details including hourly base rate, pay frequency, or pay grade level, use 'get_employee_compensation'.
    3. Before validating or auditing salary bounds for a job profile, use 'get_valid_jobs_and_locations' to verify active corporate jobs/locations, and call 'validate_pay_thresholds' to fetch standard min/max pay rates assigned to that jobCode.
    4. Treat all retrieved compensation and personnel data as highly confidential.
    ```

### 📝 Step 3: Finalize & Link to Agent
1. Name your connector **`ukg-mcp-data-connector`** and click **Create**.
2. Go to **Agents** -> Click on your agent **`gamestop-store-agent`**.
3. Link/Enable **`ukg-mcp-data-connector`** under the agent's **Data Stores** configuration tab and click **Save**.
4. Go to your agent's Chat Simulator, click the **Clear Chat (Trash)** icon, and start testing!

---

## 🧪 7. Local Client Validation (Pure Python)

To verify your tools work locally over `stdio` **without any Node/npm/gpkg package dependencies**, run the standalone client script:

```bash
source .venv/bin/activate
UKG_API_BASE_URL=https://[YOUR_MOCK_API_URL] \
python3 scripts/test_mcp_client.py
```

Enjoy your fully secure, network-integrated retail HR AI Agent!
