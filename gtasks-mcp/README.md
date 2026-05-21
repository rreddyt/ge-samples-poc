# 🧰 Google Tasks API MCP Integration Server PoC

A complete Proof of Concept (PoC) demonstrating how to integrate Google Tasks API directory mappings with **Gemini Enterprise (Vertex AI Agent Builder)** using the **Model Context Protocol (MCP)**. 

This server runs on **Google Cloud Run**, secures data access dynamically utilizing incoming end-user OAuth 2.0 access tokens, and exposes real-time task-calling capabilities to your Gemini Enterprise AI agents.

---

## 🛠️ 1. Prerequisites & GCP Configuration

Before building, deploying, and running this PoC, ensure that your Google Cloud environment has the required APIs enabled and appropriate IAM roles assigned.

### 1. Required Google Cloud APIs
Run the following command to enable all the required services in your project:
```bash
gcloud services enable \
  tasks.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  discoveryengine.googleapis.com
```

### 2. Required IAM Roles & Permissions

#### A. Deployment Identity (User or CI/CD Service Account)
The developer identity executing the Cloud Run commands requires:
* **Cloud Build Editor** (`roles/cloudbuild.builds.editor`): To compile and register the Docker image.
* **Cloud Run Developer** (`roles/run.developer`): To deploy and configure the MCP server.
* **Service Account User** (`roles/iam.serviceAccountUser`): To delegate runtime execution rights to the service accounts.
* **Project Viewer** (`roles/viewer`): To fetch basic project descriptors.

#### B. Gemini Enterprise Discovery Engine Service Account
* **Cloud Run Invoker** (`roles/run.invoker`): Granted specifically on the `gtasks-mcp-channel` service to allow Gemini Enterprise to securely call the endpoints. *(Automated in Step 4 of Deployment)*.

---

## 📂 2. PoC Project Structure

The project is organized as follows inside the `gtasks-mcp/` folder:

```text
gtasks-mcp/
├── README.md                  # This architecture and setup guide
├── Dockerfile                 # Unified container definition for Cloud Run
├── requirements.txt           # Locked Python dependencies
├── mcp/
│   ├── __init__.py
│   └── gtasks_mcp_server.py   # FastMCP Server exposing tools via stdio/HTTP
└── scripts/
    └── test_mcp_client.py     # Standalone Python client to test tools locally
```

---

## 💻 2.5 Local Virtual Environment Setup

To compile python dependencies or validate execution stdio clients locally, configure a clean virtual environment:

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

## 🧰 5. The FastMCP Server

The file **`mcp/gtasks_mcp_server.py`** implements the Model Context Protocol (MCP) server.

### Exposes 6 Tools:
1. **`list_task_lists()`**: Retrieves all task lists belonging to the authenticated user.
2. **`create_task_list(title)`**: Creates a new task list.
3. **`list_tasks(task_list_id, show_completed)`**: Retrieves all tasks inside a specific task list.
4. **`create_task(task_list_id, title, notes, due_date)`**: Creates a new task.
5. **`update_task_status(task_list_id, task_id, completed)`**: Marks a task as completed or needsAction.
6. **`delete_task(task_list_id, task_id)`**: Deletes a specific task.

### 💡 Key Design: Dynamic User OAuth Token
To protect confidential user data, **the server does not store or hardcode any Google API credentials**. 

Instead, it dynamically extracts the incoming user's OAuth Bearer token passed in the Starlette headers by Gemini Enterprise, instantiating a secure thread-safe client for every request:

```python
def get_tasks_service(ctx: Context):
    request = ctx.request_context.request if ctx.request_context else None
    auth_header = request.headers.get("authorization") if request else None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        creds = Credentials(token=token)
    else:
        # Fallback to ADC for local stdio / playground testing
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/tasks'])
    return build('tasks', 'v1', credentials=creds)
```

---

## 🚀 6. Cloud Build & Deployment Instructions

The service runs on a stateless Cloud Run container using an `env.yaml` file to securely manage all configurations.

### Step 1: Create the `env.yaml` File
Create a file named `env.yaml` in the `gtasks-mcp/` root directory:

```yaml
# env.yaml - Unified Deployment Configurations
GOOGLE_CLOUD_PROJECT: "<your-project-id>"
```

### Step 2: Load Project ID and Build the Image
Extract the project ID from `env.yaml` and build the container image via Google Cloud Build:
```bash
# Extract project ID from env.yaml
export PROJECT_ID=$(grep "GOOGLE_CLOUD_PROJECT" env.yaml | awk -F'"' '{print $2}')

# Build and register the image
gcloud builds submit --tag gcr.io/$PROJECT_ID/gtasks-mcp-poc-core:latest
```

### Step 3: Deploy the Google Tasks MCP Server
Deploy the FastMCP server to Cloud Run as a streamable HTTP application running on SSE transport:
```bash
gcloud run deploy gtasks-mcp-channel \
  --image gcr.io/$PROJECT_ID/gtasks-mcp-poc-core:latest \
  --command="python" \
  --args="mcp/gtasks_mcp_server.py" \
  --env-vars-file=env.yaml \
  --region=us-central1 \
  --allow-unauthenticated
```

### Step 4: Grant Discovery Engine Invoker Rights
Extract the project number from the project description and grant the Discovery Engine service account invoker rights:
```bash
# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant serviceAccount invoker rights
gcloud run services add-iam-policy-binding gtasks-mcp-channel \
  --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.servicesInvoker" \
  --region=us-central1
```

---

## 🧠 7. Gemini Enterprise Custom MCP Configuration

### 🔐 Google Cloud OAuth 2.0 Client Credentials Setup

To securely query the Google Tasks API, you must configure an OAuth 2.0 Client in the Google Cloud Console of your GCP Workspace.

#### Step 1: Configure the OAuth Consent Screen
1. In the Google Cloud Console, navigate to **APIs & Services** -> **OAuth consent screen**.
2. Set the User Type to **Internal** and click **Create**.
3. Add the required scope: **`https://www.googleapis.com/auth/tasks`**.
4. Save and complete the consent screen.

#### Step 2: Create OAuth 2.0 Credentials
1. Navigate to **APIs & Services** -> **Credentials** -> **+ Create Credentials** -> **OAuth client ID**.
2. Set the Application type to **`Web application`**.
3. In **Authorized redirect URIs**, add the Discovery Engine redirect callback URI:
   `https://auth.vertexaidevs.com/oauth2/callback`
4. Click **Create** and copy your **Client ID** and **Client Secret**.

---

### 📝 Custom MCP Setup Guide

To add your Google Tasks MCP server in the **Gemini Enterprise** console:

1. Navigate to **Gemini Enterprise** -> **Data Stores** -> **Create Data Store** -> **Custom MCP**.
2. Fill out the configuration exactly as mapped in the table below:

### 📝 Step 1: Connection & Auth Settings

| Field Name | Exact Value to Enter | Description |
| :--- | :--- | :--- |
| **MCP Server URL \*** | `https://[YOUR_MCP_SERVER_URL]/mcp` | **Crucial:** Must include the `/mcp` path where FastMCP serves direct HTTP POSTs. |
| **Authorization URL \*** | `https://accounts.google.com/o/oauth2/v2/auth` | Google Accounts OAuth authorization endpoint. |
| **Authorization URL Parameters** | `&access_type=offline&prompt=consent` | Mandates refresh token exchange parameters. |
| **Token URL \*** | `https://oauth2.googleapis.com/token` | Google Accounts OAuth token exchange endpoint. |
| **Client ID \*** | `[YOUR_GOOGLE_CLIENT_ID]` | Your generated Google Client ID credentials. |
| **Client Secret \*** | `[YOUR_GOOGLE_CLIENT_SECRET]` | Your generated Google Client Secret credentials. |
| **Scopes** | `openid email profile https://www.googleapis.com/auth/tasks` | **Crucial:** Include the tasks scope to allow reading/writing tasks. |

> 💡 **Important:** Click the **Login** button at the bottom of the form, authenticate with your Google account, and click **Continue**.

### 📝 Step 2: Advanced Options (Orchestrator System Prompts)

*   **MCP Server Description:**
    ```text
    A secure, read-write Google Tasks integration server. It provides real-time access to the user's task lists and task nodes. It enables the agent to query existing task lists, list active/completed tasks, create new tasks, schedule due dates, mark tasks as completed, and delete task nodes.
    ```
*   **MCP Agent Instructions:**
    ```text
    You are an expert task organization assistant. Follow these guidelines when using the Google Tasks MCP tools:
    1. To inspect the user's task lists, invoke 'list_task_lists'.
    2. To query tasks in a list, call 'list_tasks'.
    3. To schedule a new task, call 'create_task' with the target task_list_id.
    4. To mark a task complete, invoke 'update_task_status' with completed=True.
    ```

---

## 🧪 8. Local Client Validation (Pure Python)

To verify your tools work locally over `stdio` using your local gcloud auth default credentials (ADC):

```bash
# Login to your local gcloud default credentials
gcloud auth application-default login \
  --scopes="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/tasks"

source .venv/bin/activate
python3 scripts/test_mcp_client.py
```
