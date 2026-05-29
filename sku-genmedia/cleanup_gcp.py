# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess

# Early load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Disable mTLS to bypass corporate workstation cert provider checks
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = os.environ.get("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = os.environ.get("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

import google.auth
from google.cloud import bigquery
from google.cloud import storage

def cleanup_resources():
    """Undeploys the Cloud Run service and deletes the BigQuery dataset and GCS bucket."""
    
    # 1. Determine GCP configuration from environment or default context
    try:
        _, project_default = google.auth.default()
        project_id = os.environ.get("GCP_PROJECT_ID", project_default)
    except Exception:
        project_id = os.environ.get("GCP_PROJECT_ID")
        
    if not project_id:
        print("❌ Error: GCP_PROJECT_ID not set and could not be auto-detected. Please specify in your .env file.")
        return

    location = os.environ.get("GCP_LOCATION", "us-central1")
    bq_dataset = os.environ.get("BQ_DATASET", "retail_catalog_dataset")
    bucket_name = os.environ.get("GCS_BUCKET_NAME", f"retail_product_media_{project_id}")
    service_name = "sku-genmedia"

    print("=" * 80)
    print("🗑️  STARTING GCP CLEANUP SCRIPT")
    print(f"   GCP Project ID:      {project_id}")
    print(f"   Location/Region:     {location}")
    print(f"   GCS Bucket to delete: {bucket_name}")
    print(f"   BQ Dataset to delete: {bq_dataset}")
    print(f"   Cloud Run Service:   {service_name}")
    print("=" * 80)

    # Initialize clients
    try:
        bq_client = bigquery.Client(project=project_id)
        storage_client = storage.Client(project=project_id)
    except Exception as client_err:
        print(f"❌ Failed to initialize GCP clients. Ensure you are authenticated to GCP. Error: {client_err}")
        return

    # --------------------------------------------------------------------------
    # 2. Undeploy / Delete Cloud Run Service
    # --------------------------------------------------------------------------
    print(f"\n1. Deleting Cloud Run Service '{service_name}' in region '{location}'...")
    cmd = [
        "gcloud", "run", "services", "delete", service_name,
        f"--project={project_id}",
        f"--region={location}",
        "--quiet"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  🎉 Cloud Run service '{service_name}' deleted successfully!")
        else:
            if "not found" in res.stderr.lower() or "not_found" in res.stderr.lower():
                print(f"  ✓ Cloud Run service '{service_name}' not found (already deleted or not deployed).")
            else:
                print(f"  ⚠️ Warning during service deletion: {res.stderr.strip()}")
    except Exception as run_err:
        print(f"  ❌ Failed to execute gcloud command: {run_err}")

    # --------------------------------------------------------------------------
    # 3. Delete BigQuery Dataset & Tables
    # --------------------------------------------------------------------------
    print(f"\n2. Deleting BigQuery Dataset '{bq_dataset}' and all associated tables...")
    dataset_id = f"{project_id}.{bq_dataset}"
    try:
        # delete_contents=True deletes all tables inside the dataset first
        bq_client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        print(f"  🎉 BigQuery dataset '{dataset_id}' and all tables deleted successfully!")
    except Exception as bq_err:
        print(f"  ❌ Error deleting BigQuery dataset: {bq_err}")

    # --------------------------------------------------------------------------
    # 4. Delete Cloud Storage Bucket & Data
    # --------------------------------------------------------------------------
    print(f"\n3. Deleting GCS Bucket '{bucket_name}' and all its files...")
    try:
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket:
            # GCS bucket must be empty before deletion, delete all blobs first
            blobs = list(bucket.list_blobs())
            if blobs:
                print(f"  🧹 Deleting {len(blobs)} files from GCS bucket...")
                bucket.delete_blobs(blobs)
            
            bucket.delete()
            print(f"  🎉 Storage bucket '{bucket_name}' deleted successfully!")
        else:
            print(f"  ✓ Storage bucket '{bucket_name}' not found (already deleted).")
    except Exception as gcs_err:
        print(f"  ❌ Error deleting Storage bucket: {gcs_err}")

    print("\n🏁 GCP Resources Cleanup Script completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    cleanup_resources()
