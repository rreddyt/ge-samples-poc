# sku-genmedia — Premium Product Catalog Enrichment Agent

This project implements a collaborative multi-agent workflow using the **Agent Development Kit (ADK)**. The agent processes and enriches raw retail product details inside BigQuery and produces high-end marketing lifestyle images stored in Google Cloud Storage (GCS).

---

## Project Structure

```text
sku-genmedia/
├── app/
│   ├── agent.py         # Agent declarations (Tagging and Creative Image agents)
│   ├── tools.py         # Externalized tools, GCP client initializations, and configurations
│   └── app_utils/       # ADK/FastAPI typing and telemetry helpers
├── setup_gcp.py         # GCP resource provisioning (auto-populates mock BQ data & GCS images using Gemini)
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

### Step 7: Deploy the Agent
Once tested, deploy your agents-cli application directly to Cloud Run:
```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

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
