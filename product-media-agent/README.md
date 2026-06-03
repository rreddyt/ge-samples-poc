# Product Lifestyle Media Generation Agent

This project implements a collaborative marketing AI agent using the [**Agent Development Kit (ADK)**](https://adk.dev). The agent processes retail product details from a catalog inside Google BigQuery and produces
* high-end marketing lifestyle images (using `gemini-3.1-flash-image`)
* high-definition lifestyle videos (using `veo-3.1-fast-generate-001`)
The generated media is then stored in Google Cloud Storage (GCS).

---

## Project Structure

```text
product-media-agent/
├── app/
│   ├── agent.py         # Core agent definition (Media Generation agent equipped with tools)
│   ├── tools.py         # Exposed tools (BQ query catalog, Gemini Image gen, Veo Video gen, GCS upload)
│   ├── agent_runtime_app.py # Entrypoint class for Vertex AI Agent Platform Runtime (Agent Engine)
│   └── app_utils/       # ADK/FastAPI typing and telemetry helpers
├── tests/               # Unit and integration testing suites
├── GEMINI.md            # Developer onboarding instructions
└── pyproject.toml       # Python package dependencies and agents-cli configurations
```

---

## Requirements

### Authenticate to GCP
From the terminal where you're executing the agent setup, make sure the you've installed the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install), as you'll need the `gcloud` CLI. Then, log into your Google Cloud account and set up application default credentials:
```bash
gcloud init
gcloud auth application-default login
```

### Create and Activate a Python Virtual Environment
Before installing dependencies, create and activate a Python virtual environment to isolate the packages:

- cd into the product-media-agent project folder
  ```bash
  # Execute from within the repo root
  cd ./product-media-agent
  ```
  
- **Create the Virtual Environment**:
  ```bash
  python3 -m venv .venv
  ```

- **Activate the Virtual Environment**:
  - **Linux / macOS**:
    ```bash
    source .venv/bin/activate
    ```
  - **Windows (Command Prompt)**:
    ```cmd
    .venv\Scripts\activate.bat
    ```
  - **Windows (PowerShell)**:
    ```powershell
    .venv\Scripts\Activate.ps1
    ```

### Required Google Cloud IAM Roles
To execute all steps in this guide (including service API enablement, local testing, service account IAM bindings, and Agent Engine deployment), your Google Cloud identity must be granted the following IAM roles on the target GCP project:

1. **Vertex AI Administrator** (`roles/aiplatform.admin`): Required to deploy, update, and manage Vertex AI Reasoning Engine (Agent Runtime) resources.
2. **BigQuery Data Viewer** (`roles/bigquery.dataViewer`) & **BigQuery Job User** (`roles/bigquery.jobUser`): Required to run query jobs and fetch retail details from your BigQuery tables.
3. **Storage Object Admin** (`roles/storage.objectAdmin`): Required to create Cloud Storage buckets, read references, and upload/write generated lifestyle images and videos.
4. **Project IAM Admin** (`roles/resourcemanager.projectIamAdmin`): Required to execute standard IAM policy bindings for the Vertex AI Custom Code service account.
5. **Service Usage Admin** (`roles/serviceusage.serviceUsageAdmin`): Required to enable the necessary Google Cloud Service APIs in the project.

*Note: Alternatively, possessing the project **Owner** (`roles/owner`) or **Editor** (`roles/editor`) role will grant all of these required permissions.*

### Other Tools
Ensure you have installed the following:
1. **uv**: A fast Python package installer and resolver — [Install Guide](https://docs.astral.sh/uv/getting-started/installation/)
2. **agents-cli**: A single utility with the skills and commands to build, scale, govern, and optimize enterprise-grade agents. You can install by executing this in your linux terminal:
   ```bash
   uvx google-agents-cli setup
   ```
For additional installation options, see [agents-cli docs](https://docs.astral.sh/uv/getting-started/installation)

## Quick Start & Deployment

### Step 0: Enable Required Google Cloud Service APIs
Before you begin, ensure you have enabled the required APIs inside your Google Cloud project. You can do this via the Google Cloud Console or using the Google Cloud SDK CLI:

```bash
gcloud services enable aiplatform.googleapis.com \
                       bigquery.googleapis.com \
                       storage-api.googleapis.com \
                       storage-component.googleapis.com \
                       cloudresourcemanager.googleapis.com
```

---

### Step 1: Configure Environment
Make sure you've navigated into the product-media-agent project folder
```bash
# Execute from within the repo root
cd ./product-media-agent
```
Copy the environment template into a `.env` file:
```bash
cp .env.example .env
```
Edit the `.env` file and set your configuration parameters to match your Google Cloud environment:
```ini
# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1

# BigQuery Configuration
BQ_DATASET=at_home_dataset
BQ_TABLE=product_main_catalog

# Cloud Storage Configuration
GCS_BUCKET=at_home_product_lifestyle_content
```

---

### Step 2: Install Dependencies
Ensure the virtual environment is active, then install all Python dependencies using `agents-cli`:
```bash
agents-cli install
```

---

### Step 3: Run and Test the Agent Locally

You have multiple options to interact with and validate the agent locally:

- **Option A: Interactive Web Playground (Recommended)**
  Start the local ADK playground to chat with your agent visually:
  ```bash
  agents-cli playground
  ```

- **Option B: Run a Single Prompt via CLI (Fast Smoke Test)**
  Test the agent directly from the terminal without launching the UI:
  ```bash
  agents-cli run "Please generate a professional lifestyle image for product ID 12345."
  ```

- **Option C: Run the Systematic Evaluation Suite**
  Execute end-to-end evaluations against the project's configured evalsets to verify response quality and tools:
  ```bash
  agents-cli eval run --all
  ```

---

### Step 4.a: Configure Service Account Permissions (IAM)
When deployed to Vertex AI Agent Runtime (Agent Engine), the agent runs under the Vertex AI Custom Code Service Agent:
`service-<gcp-project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`

This service account must have appropriate permissions to query your BigQuery datasets and write generated marketing assets (images and videos) to your Cloud Storage bucket.

Run the following `gcloud` commands to apply these required role bindings (replace `<gcp-project-id>` with your GCP project ID, and `<gcp-project-number>` with your project number):

```bash
# 1. Grant BigQuery Job User (to run query jobs)
gcloud projects add-iam-policy-binding <gcp-project-id> \
    --member="serviceAccount:service-<gcp-project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser" \
    --condition=None

# 2. Grant BigQuery Data Viewer (to read the catalog table)
gcloud projects add-iam-policy-binding <gcp-project-id> \
    --member="serviceAccount:service-<gcp-project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    --condition=None

# 3. Grant Storage Object Admin (to upload generated images and videos)
gcloud projects add-iam-policy-binding <gcp-project-id> \
    --member="serviceAccount:service-<gcp-project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --condition=None
```

---

### Step 4.b: Deploy the Agent to Agent Engine (Agent Runtime)
Once local testing is complete, deploy your agent directly to the Agent Platform Runtime (Agent Engine). The target and execution details are automatically detected from `agents-cli-manifest.yaml`:

```bash
# Deploy the agent to Agent Runtime
agents-cli deploy --project <your-project-id> --region=us-central1
```
Upon successful completion, `agents-cli` will print the deployed **Reasoning Engine resource path** (e.g., `projects/<your-project-id>/locations/us-central1/reasoningEngines/<engine-id>`) and automatically write it to the local `deployment_metadata.json` file.

---

### Step 5: Link/Publish to a Gemini Enterprise App
After the agent is successfully deployed, you can register it under a Gemini Enterprise App to make its capabilities accessible in conversational workflows.

First, make sure you have created a Gemini Enterprise App in the Google Cloud Console under **Gemini Enterprise** -> **Apps**.

Then, register the deployed agent using one of the following methods:

#### Option A: Interactive Mode (Recommended)
The CLI will guide you through the registration process, offering to auto-detect your deployed agent and list available Gemini Enterprise Apps:
```bash
agents-cli publish gemini-enterprise --interactive
```

#### Option B: Programmatic Mode (CI/CD)
If registering programmatically or in a pipeline, provide the Gemini Enterprise App ID directly:
```bash
agents-cli publish gemini-enterprise \
  --registration-type adk \
  --gemini-enterprise-app-id "projects/<your-project-id>/locations/global/collections/default_collection/engines/<your-app-id>"
```
*Note: Because `deployment_metadata.json` is generated at deploy time, `agents-cli` will automatically auto-detect your active Agent Runtime ID and register it using the standard ADK protocol.*

---

## Parameterized Environment Variables

Configure your retail agent by adjusting the following environment variables in your `.env` file:

| Variable Name | Default Value | Description |
|---|---|---|
| `GCP_PROJECT_ID` | *None* | Your Google Cloud project identifier. |
| `GCP_LOCATION` | `us-central1` | Region for Vertex AI APIs and Cloud Storage. |
| `BQ_DATASET` | `at_home_dataset` | Name of the BigQuery dataset. |
| `BQ_TABLE` | `product_main_catalog` | BigQuery table containing source product metadata. |
| `GCS_BUCKET` | `at_home_product_lifestyle_content` | Cloud Storage bucket for generated lifestyle images and videos. |
| `GOOGLE_API_USE_CLIENT_CERTIFICATE` | `false` | Bypass developer workstation corporate certificate checks. |
| `GOOGLE_API_USE_MTLS_ENDPOINT` | `never` | Bypass developer workstation mTLS endpoints. |

---

## Usage & Prompts

You can invoke your local or deployed Agent with natural language commands. Here are example queries:

### 1. Generate a Lifestyle Image for a Single Product ID
> "Please generate a professional lifestyle image for product ID 12345."
- To include specific creative instructions:
> "Please generate a lifestyle image for product ID 12345. Additional instructions: Show the product resting on a sleek modern wooden dining table during sunset."

### 2. Generate a Lifestyle Video for a Single Product ID
> "Please generate a premium lifestyle video shot for product ID 54321."
- To include specific camera movement or styling instructions:
> "Please generate a lifestyle video for product ID 54321. Additional instructions: Panning camera view, bright cozy living room setting."

### 3. Batch Image Generation for Multiple Products
> "Batch generate lifestyle images for the first 3 products."
- This will fetch the first 3 products from BigQuery and generate a lifestyle image for each.
