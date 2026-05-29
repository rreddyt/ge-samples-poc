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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Workstation mTLS Bypass Defaults (overridable via .env)
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = os.environ.get("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = os.environ.get("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

import google.auth
from google.cloud import bigquery
from google.cloud import storage
from google.genai import types
import uuid

# ---------------------------------------------------------
# Initialize Environment & GCP Clients
# ---------------------------------------------------------
# Retrieve configurations from environment, dynamically falling back to detected GCP project ID
_, project_default = google.auth.default()
project_id = os.environ.get("GCP_PROJECT_ID", project_default)

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GCP_LOCATION", "us-central1")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

bq_client = bigquery.Client(project=project_id)
storage_client = storage.Client(project=project_id)

# Parameterized BigQuery dataset and table names (defaulting to generic retail names)
bq_dataset = os.environ.get("BQ_DATASET", "retail_catalog_dataset")
bq_products_table = os.environ.get("BQ_PRODUCTS_TABLE", "products")
bq_tags_table = os.environ.get("BQ_TAGS_TABLE", "product_tags")

products_table_id = f"{project_id}.{bq_dataset}.{bq_products_table}"
tags_table_id = f"{project_id}.{bq_dataset}.{bq_tags_table}"

# Parameterized Cloud Storage bucket name (defaulting to generic retail name)
bucket_name = os.environ.get("GCS_BUCKET_NAME", f"retail_product_media_{project_id}")

# ---------------------------------------------------------
# Define Core Workflow Tools
# ---------------------------------------------------------

def update_bq_tags(sku: str, tags: list[str]) -> str:
    """Tool to insert or update generated product tags into a separate BigQuery table.

    Args:
        sku: The unique product SKU (Stock Keeping Unit) identifier.
        tags: A list of 5-10 highly descriptive tags generated for product categorization.

    Returns:
        A confirmation message indicating whether the operation was successful.
    """
    if not sku or not isinstance(sku, str):
        return "Error: Invalid SKU format provided."
    if not tags or not isinstance(tags, list):
        return "Error: Invalid tags list provided."

    tags_str = ", ".join([str(t).strip() for t in tags if t])

    try:
        # Security: Prevent SQL injection by using parameterized upsert query (MERGE)
        query = f"""
        MERGE `{tags_table_id}` T
        USING (SELECT @sku AS sku) S
        ON T.sku = S.sku
        WHEN MATCHED THEN
          UPDATE SET tags = @tags
        WHEN NOT MATCHED THEN
          INSERT (sku, tags) VALUES (@sku, @tags)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tags", "STRING", tags_str),
                bigquery.ScalarQueryParameter("sku", "STRING", sku),
            ]
        )
        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()  # Wait for query to complete
        return f"Successfully stored tags for SKU {sku} in separate table `{tags_table_id}`: {tags_str}"
    except Exception as e:
        return f"Error updating tags in table `{tags_table_id}` for SKU {sku}: {str(e)}"


def generate_lifestyle_image(sku: str, product_name: str, product_image_url: str, prompt: str) -> str:
    """Tool to generate a brand-aligned lifestyle image using Imagen 3 and save it to Cloud Storage with custom metadata.

    Args:
        sku: The unique product SKU identifier.
        product_name: The official name/title of the product.
        product_image_url: The GCS or HTTP URL of the original product image.
        prompt: A detailed aesthetic scene description for Imagen to render the product in a lifestyle scenario.

    Returns:
        The GCS path (gs://...) where the generated lifestyle image is stored.
    """
    from google import genai
    import uuid
    
    if not sku or not prompt:
        return "Error: SKU and creative prompt are required."

    # Generate unique Image ID
    image_id = f"img-{uuid.uuid4().hex[:12]}"
    destination_blob_name = f"lifestyle_images/{sku}_{image_id}.png"

    try:
        # Initialize standard GenAI Client (configured for Vertex AI in environment)
        client = genai.Client()
        
        # Call standard Vertex AI Imagen 3 model
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:3",
                person_generation="ALLOW_ADULT",
                output_mime_type="image/png",
            )
        )

        if not response.generated_images:
            return "Error: Imagen model returned no generated images."

        generated_image = response.generated_images[0]
        image_bytes = generated_image.image.image_bytes

        # Store generated lifestyle image in GCS with SKU, Image ID, and Image Description as metadata
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Set GCS custom blob metadata
        blob.metadata = {
            "Product SKU": sku,
            "Image ID": image_id,
            "Image Description": prompt
        }
        
        blob.upload_from_string(image_bytes, content_type="image/png")

        return f"gs://{bucket_name}/{destination_blob_name}"
    except Exception as e:
        return f"Error generating or uploading lifestyle image for SKU {sku}: {str(e)}"


def list_product_360_images(sku: str) -> list[str]:
    """Tool to list all available 360-degree product image URIs stored in Cloud Storage for a given SKU.

    Args:
        sku: The unique product SKU identifier.

    Returns:
        A list of GCS URIs (gs://...) pointing to the product's images from all angles (front, side, back, etc.).
    """
    if not sku or not isinstance(sku, str):
        return ["Error: Invalid SKU format."]

    prefix = f"products/{sku}_360/"
    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
        uris = [f"gs://{bucket_name}/{blob.name}" for blob in blobs if blob.name.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not uris:
            return [f"Warning: No images found in GCS under prefix '{prefix}' for SKU {sku}."]
        return uris
    except Exception as e:
        return [f"Error listing 360 images for SKU {sku}: {str(e)}"]


def read_category_guidelines(category: str) -> str:
    """Tool to read category-specific lifestyle styling guidelines from Cloud Storage.

    Args:
        category: The product category name (e.g. 'Pillows', 'Furniture', 'Lighting').

    Returns:
        The text content of the styling and image guidelines.
    """
    if not category or not isinstance(category, str):
        return "Error: Invalid category provided."

    blob_name = f"category_guidelines/{category.strip()}/guidelines.txt"
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return f"Warning: No guidelines document found in GCS for category '{category}'."
        text = blob.download_as_text()
        return text
    except Exception as e:
        return f"Error reading guidelines for category '{category}': {str(e)}"
