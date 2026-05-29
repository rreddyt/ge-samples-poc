# sku-genmedia — Premium Product Catalog Enrichment Agent

This project implements a collaborative multi-agent workflow using the **Agent Development Kit (ADK)**. The agent processes and enriches raw retail product details inside BigQuery and produces high-end marketing lifestyle images stored in Google Cloud Storage (GCS).

---

## Project Structure

```text
sku-genmedia/
├── app/
│   ├── agent.py         # Agent declarations (Tagging and Creative Image agents)
│   ├── tools.py         # Externalized tools, GCP client initializations, and configurations
│   ├── agent_runtime_app.py # Entrypoint class for Vertex AI Agent Platform Runtime (Agent Engine)
│   └── app_utils/       # ADK/FastAPI typing and telemetry helpers
├── setup_gcp.py         # GCP resource provisioning (auto-populates mock BQ data & GCS images using Gemini)
├── cleanup_gcp.py       # GCP resource teardown (undeploys reasoning engine, BQ dataset and GCS bucket)
├── gen-script.py        # CLI runner to execute the collaborative agent workflow at scale
├── tests/               # Unit and integration testing suites
├── GEMINI.md            # Developer onboarding instructions
└── pyproject.toml       # Python package dependencies and agents-cli configurations
```

---

## Requirements

Ensure you have installed the following:
1. **uv**: A fast Python package installer and resolver — [Install Guide](https://docs.astral.sh/uv/getting-started/installation/)
2. **agents-cli**: The standard ADK agent development utility — Install via `uv tool install google-agents-cli`
3. **Google Cloud SDK**: The `gcloud` command-line interface — [Install Guide](https://cloud.google.com/sdk/docs/install)

---

## Quick Start & Deployment

### Step 1: Authenticate to GCP
Login to your Google Cloud account and set up application default credentials:
```bash
gcloud auth login
gcloud auth application-default login
```

### Step 2: Configure Environment
Copy the environment template into a `.env` file:
```bash
cp .env.example .env
```
Edit the `.env` file and set your configuration parameters:
- `GCP_PROJECT_ID`: Set to your target GCP Project ID.
- `GCS_BUCKET_NAME`: Set to a globally unique bucket name where mock data and generated lifestyle images will reside.

Other configuration variables (`BQ_DATASET`, `BQ_PRODUCTS_TABLE`, etc.) are already preset with generic retail store defaults.

### Step 3: Install Dependencies
Install Python packages using `agents-cli`:
```bash
agents-cli install
```

### Step 4: Provision GCP Mock Data & Images
Run the setup script to automatically provision the BigQuery dataset/tables, create the GCS bucket, upload category-specific guidelines, and populate mock retail catalog details:
```bash
uv run python setup_gcp.py
```
> 💡 **How it works:** `setup_gcp.py` connects to Gemini (`gemini-2.5-flash`) to dynamically generate structured product descriptions, and then uses Imagen 3 (`imagen-3.0-generate-002`) to generate corresponding professional product pictures for 360-degree angles (front, side, back). It automatically falls back to offline solid color placeholder PNGs if APIs are not fully configured in your project yet.

### Step 5: Run locally in ADK Playground
Start the local ADK playground to interact with the agents visually:
```bash
agents-cli playground
```

### Step 6: Run Batch enrichment workflow
To execute the multi-agent workflow on all mock products inside BigQuery:
```bash
uv run python gen-script.py
```

### Step 7: Deploy the Agent to Agent Engine (Agent Platform Runtime)
Once local testing in the playground is complete, deploy your agent directly to the Vertex AI Agent Platform Runtime (Agent Engine):
```bash
# 1. Set your active GCP project ID
gcloud config set project <your-project-id>

# 2. Deploy the agent to Agent Runtime
agents-cli deploy --deployment-target agent_runtime --region=us-central1
```
Upon successful completion, `agents-cli` will print the deployed **Reasoning Engine resource path** (e.g., `projects/<your-project-id>/locations/us-central1/reasoningEngines/<engine-id>`) and automatically write it to the `deployment_metadata.json` file.

---

### Step 8: Invoke and Test the Deployed Agent
There are two main ways to query and test your deployed reasoning engine:

#### Option A: Using the `agents-cli` command-line runner (Recommended for testing A2A)
The ADK CLI provides a built-in runner that handles authentication and invokes the reasoning engine utilizing the **Agent-to-Agent (A2A)** protocol:
```bash
# Invoke via A2A protocol
agents-cli run --url https://us-central1-aiplatform.googleapis.com/v1/projects/<your-project-id>/locations/us-central1/reasoningEngines/<engine-id> \
  --mode a2a \
  "Please execute the enrichment workflow for the product catalog. SKU: SKU-10948 Name: Boho Chic Tufted Throw Pillow Description: Cream tufted throw pillow Category: Pillows"
```
*Replace `<your-project-id>` and `<engine-id>` with your actual deployment coordinates.*

#### Option B: Programmatically via the Vertex AI SDK in Python
You can load and invoke the deployed reasoning engine directly inside a Python script or Jupyter notebook:
```python
import vertexai

# 1. Initialize Vertex AI
vertexai.init(project="<your-project-id>", location="us-central1")

# 2. Retrieve the deployed reasoning engine
client = vertexai.Client(location="us-central1")
agent = client.agent_engines.get(
    name="projects/<your-project-id>/locations/us-central1/reasoningEngines/<engine-id>"
)

# 3. Query the agent
message = """
Please execute the enrichment workflow for the product catalog.
Product Details:
SKU: SKU-10948
Name: Boho Chic Tufted Throw Pillow
Description: A gorgeous, cream-colored woven cotton throw pillow.
Category: Pillows
"""
async for event in agent.async_stream_query(message=message, user_id="test_user"):
    print(event)
```

---



---

## Parameterized Environment Variables

Configure your retail agent by adjusting the following environment variables in your `.env` file:

| Variable Name | Default Value | Description |
|---|---|---|
| `GCP_PROJECT_ID` | *None* | Your Google Cloud project identifier. |
| `GCP_LOCATION` | `us-central1` | Region for Vertex AI APIs and Cloud Storage. |
| `BQ_DATASET` | `retail_catalog_dataset` | Name of the BigQuery dataset. |
| `BQ_PRODUCTS_TABLE` | `products` | BigQuery table containing source product metadata. |
| `BQ_TAGS_TABLE` | `product_tags` | BigQuery destination table to store generated marketing tags. |
| `GCS_BUCKET_NAME` | `retail_product_media_<project_id>` | Cloud Storage bucket for category guidelines and images. |
| `GOOGLE_API_USE_CLIENT_CERTIFICATE` | `false` | Bypass developer workstation corporate certificate checks. |
| `GOOGLE_API_USE_MTLS_ENDPOINT` | `never` | Bypass developer workstation mTLS endpoints. |

---

## Development & Testing

- Run all integration and unit tests:
  ```bash
  uv run pytest tests/unit tests/integration
  ```
- Lint the codebase for quality assurance:
  ```bash
  agents-cli lint
  ```
- Add Terraform infrastructure pipelines or CI/CD workflows:
  ```bash
  agents-cli scaffold enhance
  ```

---

## 🧹 GCP Teardown & Cleanup

To completely undeploy the Agent Platform reasoning engine and destroy all associated BigQuery tables/data and Cloud Storage buckets/media, simply execute the cleanup script:
```bash
uv run python cleanup_gcp.py
```
This script automatically:
- Undeploys and deletes the **`sku-genmedia`** reasoning engine instance from Vertex AI Agent Platform in the target GCP region.
- Deletes the entire BigQuery dataset containing the source products table and enriched tags table recursively.
- Deletes all uploaded folders, category guidelines, and Imagen-generated assets inside the GCS bucket, before deleting the bucket itself.


