# 🧰 UKG Pro (HR/Payroll) MCP Integration Server PoC

A complete Proof of Concept (PoC) demonstrating how to integrate a retail store HR and Compensation system (UKG Pro) with **Gemini Enterprise (Vertex AI Agent Builder)** using the **Model Context Protocol (MCP)**. 

This server runs on **Google Cloud Run**, is backed by a mock dataset in **Google BigQuery**, and exposes secure, real-time tool-calling capabilities to your Gemini Enterprise AI agents.

---

## 🛠️ 1. Prerequisites & GCP Configuration

Before building, deploying, and running this PoC, ensure that your Google Cloud environment has the required APIs enabled and appropriate IAM roles assigned.

### 1. Required Google Cloud APIs
Run the following command to enable all the required services in your project:
```bash
gcloud services enable \
  bigquery.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  discoveryengine.googleapis.com
```

### 2. Required IAM Roles & Permissions

#### A. Deployment Identity (User or CI/CD Service Account)
The developer identity executing the BigQuery setup scripts and Cloud Run commands requires:
* **BigQuery Admin** (`roles/bigquery.admin`): To create the dataset, construct tables, and load mock records.
* **Cloud Build Editor** (`roles/cloudbuild.builds.editor`): To compile and register the Docker image.
* **Cloud Run Developer** (`roles/run.developer`): To deploy and configure both the API and MCP server.
* **Service Account User** (`roles/iam.serviceAccountUser`): To delegate runtime execution rights to the service accounts.
* **Project Viewer** (`roles/viewer`): To fetch basic project descriptors.

#### B. Cloud Run Runtime Service Account
By default, Cloud Run services run under the **Compute Engine Default Service Account** (`{project_number}-compute@developer.gserviceaccount.com`). If you are securing the default or using a custom runtime service account, it must have the following roles:
* **BigQuery Data Viewer** (`roles/bigquery.dataViewer`): To read and select data from the mock employee tables.
* **BigQuery Job User** (`roles/bigquery.jobUser`): To execute query jobs in the BigQuery project.

#### C. Gemini Enterprise Discovery Engine Service Account
* **Cloud Run Invoker** (`roles/run.invoker`): Granted specifically on the `ukg-mcp-channel` service to allow Gemini Enterprise to securely call the endpoints. *(Automated in Step 6 of Deployment)*.

---

## 📂 2. PoC Project Structure

The project is organized as follows inside the `ukg-mock-api-mcp/` folder:

```text
ukg-mock-api-mcp/
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

## 💻 2.5 Local Virtual Environment Setup

To compile python dependencies, seed BigQuery datasets, or validate execution stdio clients locally, configure a clean virtual environment:

```bash
# 1. Create a clean Python virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Generate OAuth token to bypass package registry airlocks
export ARTIFACT_REGISTRY_TOKEN=$(gcloud auth application-default print-access-token)

# 4. Install project dependencies inside the active virtual environment
UV_NO_CONFIG=1 \
UV_INDEX_URL=https://pypi.org/simple \
UV_EXTRA_INDEX_URL="https://oauth2accesstoken:${ARTIFACT_REGISTRY_TOKEN}@us-python.pkg.dev/artifact-foundry-prod/ah-3p-staging-python/simple/" \
pip install -r requirements.txt
```

---

## 🗄️ 3. BigQuery Sample Data Setup

The mock UKG data is hosted directly in Google BigQuery. The schema represents employee personal details, compensation rates, corporate job profiles, and retail organizational levels.

### Schema & Sample Records

| Table Name | Key Fields | Sample Records / Mock Data |
| :--- | :--- | :--- |
| **`person_details`** | `employeeId`, `firstName`, `lastName`, `email` | `EMP1001` (Alex Mercer), `EMP1002` (Sarah Connor), `EMP1003` (David Miller) |
| **`employment_details`** | `employeeId`, `jobTitle`, `primaryJobCode`, `supervisorName`, `orgLevel` | `EMP1001` -> Senior Sales Associate (`SGA01`), supervisor `Sarah Connor`, store `4550` |
| **`compensation_details`** | `employeeId`, `hourlyPayRate`, `annualSalary`, `payFrequency`, `payGrade` | `EMP1001` -> **$16.50/hr** ($34,320/yr), hourly, **GRADE_B** |
| **`pay_grades`** | `jobCode`, `payGrade`, `minimumPayRate`, `maximumPayRate` | `GA01` (Sales Associate) -> Min: **$13.00**, Max: **$15.50** |
| **`job_profiles`** | `jobCode`, `jobTitle`, `isActive` | `GA01` (Sales Associate), `SGA01` (Senior Sales Associate), `SL01` (Store Manager) |
| **`org_levels`** | `orgLevel` (Store #), `storeName`, `isActive` | `4550` (Retail Store - Austin Central), `1024` (Retail Store - Dallas North) |

### Automating Creation
You can regenerate the entire dataset, tables, and sample rows by executing the Python script. It automatically honors the BQ_DATASET environment variable if defined:
```bash
source .venv/bin/activate
GOOGLE_API_USE_MTLS_ENDPOINT=never GOOGLE_API_USE_CLIENT_CERTIFICATE=false \
BQ_DATASET="<your-project-id>.<your-dataset-name>" \
python3 scripts/setup_bq_mock_data.py
```

---

## 🌐 4. FastAPI Mock UKG REST API

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

## 🧰 5. The FastMCP Server

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

## 🚀 6. Cloud Build & Deployment Instructions

Both services run from the same container image `ukg-mcp-poc-core:latest` but start with different execution commands. 

We use an `env.yaml` file to securely manage all project configurations and avoid hardcoding parameters in shell commands.

### Step 1: Create the `env.yaml` File
Create a file named `env.yaml` in the `ukg-mock-api-mcp/` root directory with placeholders:

```yaml
# env.yaml - Unified Deployment Configurations
GOOGLE_CLOUD_PROJECT: "<your-project-id>"
BQ_DATASET: "<your-project-id>.<your-dataset-name>"
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

## 🧠 7. Gemini Enterprise Custom MCP Configuration

### 🔐 Google Cloud OAuth 2.0 Client Credentials Setup

To securely connect Gemini Enterprise (Vertex AI Agent Builder) to your Cloud Run MCP server, you must configure an OAuth 2.0 Client in the Google Cloud Console. This generates the required **Client ID** and **Client Secret** credentials.

#### Step 1: Configure the OAuth Consent Screen
1. In the Google Cloud Console, navigate to **APIs & Services** -> **OAuth consent screen**.
2. Select the **User Type**:
   * **Internal:** (Recommended) Restricts access strictly to users within your Google Workspace organization.
   * **External:** Opens access to other Google accounts.
3. Click **Create**.
4. Fill in the required fields:
   * **App name:** e.g. `Gemini Enterprise MCP Connector`
   * **User support email:** Select your Workspace email.
   * **Developer contact information:** Enter your email.
5. Click **Save and Continue** through the Scopes and Test Users tabs, then click **Back to Dashboard**.

#### Step 2: Create OAuth 2.0 Credentials
1. Navigate to **APIs & Services** -> **Credentials**.
2. Click **+ Create Credentials** at the top of the screen and select **OAuth client ID**.
3. Set the **Application type** to **`Web application`**.
4. Enter a name for the client: e.g., `Gemini Enterprise MCP Client`.
5. In the **Authorized redirect URIs** section, click **+ ADD URI** and enter the official Gemini Enterprise callback redirect endpoint: `https://vertexaisearch.cloud.google.com/oauth-redirect`
6. Click **Create**.
7. A dialog will appear displaying your **Client ID** and **Client Secret**. Copy these values securely—you will use them in Step 1 to link the connector!

---

### 📝 Custom MCP Setup Guide

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
2. Go to **Agents** -> Click on your agent **`retail-store-agent`**.
3. Link/Enable **`ukg-mcp-data-connector`** under the agent's **Data Stores** configuration tab and click **Save**.
4. Go to your agent's Chat Simulator, click the **Clear Chat (Trash)** icon, and start testing!

---

## 🧪 8. Local Client Validation (Pure Python)

To verify your tools work locally over `stdio` **without any Node/npm/gpkg package dependencies**, run the standalone client script:

```bash
source .venv/bin/activate
UKG_API_BASE_URL=https://[YOUR_MOCK_API_URL] \
python3 scripts/test_mcp_client.py
```

Enjoy your fully secure, network-integrated retail HR AI Agent!
