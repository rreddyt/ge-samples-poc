# sku-genmedia — Premium Product Lifestyle Content Generation Agent

This project implements a collaborative ADK marketing agent using the **Agent Development Kit (ADK)**. The agent processes retail product details inside Google BigQuery and produces high-end marketing lifestyle images (using `gemini-3.1-flash-image`) and high-definition lifestyle videos (using `veo-3.1-fast-generate-001`) stored in Google Cloud Storage (GCS).

---

## Project Structure

```text
sku-genmedia/
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

### Step 3: Install Dependencies
Install Python packages using `agents-cli`:
```bash
agents-cli install
```

### Step 4: Run locally in ADK Playground
Start the local ADK playground to interact with the agent visually:
```bash
agents-cli playground
```

### Step 5: Deploy the Agent to Agent Engine (Agent Runtime)
Once local testing in the playground is complete, deploy your agent directly to the Vertex AI Agent Engine (Agent Runtime):
```bash
# 1. Set your active GCP project ID
gcloud config set project <your-project-id>

# 2. Deploy the agent to Agent Runtime
agents-cli deploy --deployment-target agent_runtime --region=us-central1
```
Upon successful completion, `agents-cli` will print the deployed **Reasoning Engine resource path** (e.g., `projects/<your-project-id>/locations/us-central1/reasoningEngines/<engine-id>`) and automatically write it to the local `deployment_metadata.json` file.

---

### Step 6: Link/Publish to a Gemini Enterprise App
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
  --registration-type a2a \
  --gemini-enterprise-app-id "projects/<your-project-id>/locations/global/collections/default_collection/engines/<your-app-id>"
```
*Note: Because `deployment_metadata.json` is generated at deploy time, `agents-cli` will automatically auto-detect your active Agent Runtime ID and register it using the Agent-to-Agent (A2A) protocol.*

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
