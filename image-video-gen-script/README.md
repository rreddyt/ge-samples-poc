# Product Lifestyle Content Generator

A premium Python script that utilizes the latest **Google Gemini Multimodal APIs** (`gemini-3.1-flash-image` and `veo-3.1-fast-generate-001`) to generate professional, premium lifestyle images and videos for retail products stored in Google BigQuery, and uploads the generated results to Google Cloud Storage (GCS).

---

## Features

- **Interactive Terminal UI**: Choose between three generation modes seamlessly.
- **Single Product Image Generation**: Generate high-quality lifestyle images for a specific product ID with optional custom styling instructions.
- **Single Product Video Generation**: Generate 8-second premium lifestyle videos for a specific product ID using Gemini Video APIs.
- **Batch Lifestyle Image Generation**: Process first $N$ items from your BigQuery product catalog in a single run.
- **Robust Fallback Mechanisms**: Seamlessly creates fallback folders and buckets in GCS if configuration variables are missing or target locations don't exist.
- **Zero-Dependency Environment Loader**: Uses a built-in `.env` parser requiring no third-party dependencies for configuration storage.

---

## Prerequisites

1. **Python**: Ensure you have Python 3.10 or newer installed.
2. **Google Cloud CLI**: Installed and authenticated to your Google Cloud project.
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
3. **Permissions**: Ensure your Google Cloud identity has the necessary permissions for:
   - Vertex AI / Gemini API access
   - BigQuery (Reader)
   - Google Cloud Storage (Writer / Bucket Creator)

---

## Installation & Setup

### 0. Enable Required Google Cloud Service APIs
Before you begin, ensure you have enabled the required APIs inside your Google Cloud project:

```bash
gcloud services enable aiplatform.googleapis.com \
                       bigquery.googleapis.com \
                       storage-api.googleapis.com \
                       storage-component.googleapis.com \
                       cloudresourcemanager.googleapis.com
```

### 1. Create a Virtual Environment
Create a clean virtual environment named `.venv` to isolate the dependencies:
```bash
python3 -m venv .venv
```

### 2. Activate the Virtual Environment
Activate the virtual environment before installing dependencies:

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

### 3. Install Dependencies
Install all required Python packages using the provided `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration (`.env`)

All configurations are loaded dynamically from a local `.env` file. 

### 1. Create your `.env` file
Make a copy of the `.env.example` template file:
```bash
cp .env.example .env
```

### 2. Fill in the Configuration Values
Open the newly created `.env` file in your favorite text editor and customize the values to match your Google Cloud environment:
```ini
# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1

# BigQuery Configuration
BQ_DATASET=your_bigquery_dataset
BQ_TABLE=product_main_catalog

# Cloud Storage Configuration
GCS_BUCKET=your_gcs_bucket_name
```

---

## Usage

Once configuration is complete and your virtual environment is activated, run the script:

```bash
python image-video-gen.py
```

### Generation Modes
Upon execution, the script will prompt you with three options:
1. **Option 1 (Single Product Image)**: Generates a 2K lifestyle image for a given `PRODUCT_ID`. You can append additional creative instructions (e.g. `"Show the product on a wooden coffee table during sunset"`).
2. **Option 2 (Single Product Video)**: Generates an 8-second, 1080p lifestyle video for a given `PRODUCT_ID`.
3. **Option 3 (Batch Image Generation)**: Queries BigQuery and generates lifestyle images for the first $N$ products in the table.

---

## Project Structure

- `image-video-gen.py`: The core execution script.
- `requirements.txt`: Python package dependencies.
- `.env.example`: Example configuration template.
- `.env`: Active configuration file containing credentials & paths (git-ignored).
- `README.md`: Setup and usage instructions (this document).
