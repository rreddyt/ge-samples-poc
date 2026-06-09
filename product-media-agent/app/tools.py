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
import io
import time
import json
import re
import requests
from datetime import datetime
from PIL import Image

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Disable client certificate checks to avoid mTLS helper segfault issues in this environment
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

import google.auth
from google.cloud import bigquery
from google.cloud import storage
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

# Retrieve configurations from environment
_, project_default = google.auth.default()
project_id = os.environ.get("GCP_PROJECT_ID", project_default)
gemini_location = os.environ.get("GEMINI_LOCATION", os.environ.get("GCP_LOCATION", "us-central1"))
veo_location = os.environ.get("VEO_LOCATION", "us-central1")
image_location = os.environ.get("IMAGE_LOCATION", "global")

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# BigQuery Configuration
bq_dataset = os.environ.get("BQ_DATASET", "at_home_dataset")
bq_table = os.environ.get("BQ_TABLE", "product_main_catalog")
bq_status_table = os.environ.get("BQ_STATUS_TABLE", "media_generation_status")
bq_location = os.environ.get("BQ_LOCATION", "us-central1")

from typing import Optional

def _ensure_status_table_exists(client: bigquery.Client) -> str:
    table_ref = client.dataset(bq_dataset).table(bq_status_table)
    try:
        client.get_table(table_ref)
        return f"{project_id}.{bq_dataset}.{bq_status_table}"
    except Exception:
        # Create table if it doesn't exist
        schema = [
            bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("lifestyle_media_file_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("gcs_authenticated_file_path", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("generation_date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("generation_status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("last_reviewed_date", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("review_status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("generation_failure_msg", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("media_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("media_format", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("generated_by", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("reviewed_by", "STRING", mode="NULLABLE"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
        print(f"Created BigQuery status table: {bq_dataset}.{bq_status_table}")
        return f"{project_id}.{bq_dataset}.{bq_status_table}"

def start_media_generation_status(
    product_id: str,
    filename: str,
    old_lifestyle_media_file_name: Optional[str] = None,
    generated_by: Optional[str] = None
) -> None:
    """Inserts a PENDING log or updates the existing rejected log to PENDING in BigQuery."""
    client = get_bq_client()
    table_fullname = _ensure_status_table_exists(client)
    from datetime import datetime
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    ext = filename.lower().split(".")[-1]
    media_format = ext.upper()
    if ext in ("jpg", "jpeg", "png"):
        media_type = "Image"
    elif ext == "mp4":
        media_type = "Video"
    else:
        media_type = "Unknown"

    if old_lifestyle_media_file_name:
        # Update existing record
        query = f"""
            UPDATE `{table_fullname}`
            SET lifestyle_media_file_name = @new_lifestyle_media_file_name,
                gcs_authenticated_file_path = NULL,
                generation_status = 'PENDING',
                last_reviewed_date = NULL,
                review_status = 'PENDING',
                generation_failure_msg = NULL,
                generation_date = @generation_date,
                media_type = @media_type,
                media_format = @media_format,
                generated_by = @generated_by,
                reviewed_by = NULL
            WHERE product_id = @product_id AND lifestyle_media_file_name = @old_lifestyle_media_file_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("new_lifestyle_media_file_name", "STRING", filename),
                bigquery.ScalarQueryParameter("generation_date", "TIMESTAMP", now_str),
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("old_lifestyle_media_file_name", "STRING", old_lifestyle_media_file_name),
                bigquery.ScalarQueryParameter("media_type", "STRING", media_type),
                bigquery.ScalarQueryParameter("media_format", "STRING", media_format),
                bigquery.ScalarQueryParameter("generated_by", "STRING", generated_by),
            ]
        )
    else:
        # Insert a new record
        query = f"""
            INSERT INTO `{table_fullname}` (
                product_id,
                lifestyle_media_file_name,
                gcs_authenticated_file_path,
                generation_date,
                generation_status,
                last_reviewed_date,
                review_status,
                generation_failure_msg,
                media_type,
                media_format,
                generated_by,
                reviewed_by
            ) VALUES (
                @product_id,
                @lifestyle_media_file_name,
                NULL,
                @generation_date,
                'PENDING',
                NULL,
                'PENDING',
                NULL,
                @media_type,
                @media_format,
                @generated_by,
                NULL
            )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("lifestyle_media_file_name", "STRING", filename),
                bigquery.ScalarQueryParameter("generation_date", "TIMESTAMP", now_str),
                bigquery.ScalarQueryParameter("media_type", "STRING", media_type),
                bigquery.ScalarQueryParameter("media_format", "STRING", media_format),
                bigquery.ScalarQueryParameter("generated_by", "STRING", generated_by),
            ]
        )
    query_job = client.query(query, job_config=job_config)
    query_job.result()


def update_media_generation_status_result(
    product_id: str,
    lifestyle_media_file_name: str,
    generation_status: str,
    gcs_authenticated_file_path: Optional[str] = None,
    generation_failure_msg: Optional[str] = None
) -> None:
    """Updates an existing media generation log row in BigQuery with success/failure results."""
    client = get_bq_client()
    table_fullname = _ensure_status_table_exists(client)
    from datetime import datetime
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
        UPDATE `{table_fullname}`
        SET generation_status = @generation_status,
            gcs_authenticated_file_path = @gcs_authenticated_file_path,
            generation_failure_msg = @generation_failure_msg,
            generation_date = @generation_date
        WHERE product_id = @product_id AND lifestyle_media_file_name = @lifestyle_media_file_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("generation_status", "STRING", generation_status),
            bigquery.ScalarQueryParameter("gcs_authenticated_file_path", "STRING", gcs_authenticated_file_path),
            bigquery.ScalarQueryParameter("generation_failure_msg", "STRING", generation_failure_msg),
            bigquery.ScalarQueryParameter("generation_date", "TIMESTAMP", now_str),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("lifestyle_media_file_name", "STRING", lifestyle_media_file_name),
        ]
    )
    query_job = client.query(query, job_config=job_config)
    query_job.result()


def log_media_generation_status(
    product_id: str,
    lifestyle_media_file_name: str,
    gcs_authenticated_file_path: Optional[str],
    generation_status: str,
    generation_failure_msg: Optional[str] = None
) -> str:
    """Inserts a row into the media generation status BigQuery table log.
    
    Args:
        product_id: The product ID.
        lifestyle_media_file_name: The file name of the image/video.
        gcs_authenticated_file_path: The authenticated HTTPS URL to the GCS file (None if failed).
        generation_status: "SUCCESS" or "FAILURE".
        generation_failure_msg: The error message if failed.
        
    Returns:
        A JSON string indicating success or failure of the logging operation.
    """
    try:
        client = get_bq_client()
        table_fullname = _ensure_status_table_exists(client)
        
        from datetime import datetime
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        query = f"""
            INSERT INTO `{table_fullname}` (
                product_id,
                lifestyle_media_file_name,
                gcs_authenticated_file_path,
                generation_date,
                generation_status,
                last_reviewed_date,
                review_status,
                generation_failure_msg
            ) VALUES (
                @product_id,
                @lifestyle_media_file_name,
                @gcs_authenticated_file_path,
                @generation_date,
                @generation_status,
                NULL,
                'PENDING',
                @generation_failure_msg
            )
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("lifestyle_media_file_name", "STRING", lifestyle_media_file_name),
                bigquery.ScalarQueryParameter("gcs_authenticated_file_path", "STRING", gcs_authenticated_file_path),
                bigquery.ScalarQueryParameter("generation_date", "TIMESTAMP", now_str),
                bigquery.ScalarQueryParameter("generation_status", "STRING", generation_status),
                bigquery.ScalarQueryParameter("generation_failure_msg", "STRING", generation_failure_msg),
            ]
        )
        query_job = client.query(query, job_config=job_config)
        query_job.result() # Wait for completion
            
        return json.dumps({"status": "success", "message": "Log entry inserted successfully."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to insert log: {str(e)}"})

def approve_media_review(
    product_id: str,
    lifestyle_media_file_name: str,
    tool_context: ToolContext = None
) -> str:
    """Updates the review status of a generated media file to APPROVED in the status table.
    
    Args:
        product_id: The product ID.
        lifestyle_media_file_name: The file name of the reviewed media.
        
    Returns:
        A JSON string indicating success or failure of the update operation.
    """
    try:
        client = get_bq_client()
        table_fullname = _ensure_status_table_exists(client)
        
        from datetime import datetime
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        reviewer = tool_context.user_id if tool_context else None

        query = f"""
            UPDATE `{table_fullname}`
            SET review_status = 'APPROVED', 
                last_reviewed_date = @now,
                reviewed_by = @reviewed_by
            WHERE product_id = @product_id AND lifestyle_media_file_name = @lifestyle_media_file_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("now", "TIMESTAMP", now_str),
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("lifestyle_media_file_name", "STRING", lifestyle_media_file_name),
                bigquery.ScalarQueryParameter("reviewed_by", "STRING", reviewer),
            ]
        )
        query_job = client.query(query, job_config=job_config)
        query_job.result() # Wait for completion
        
        return json.dumps({"status": "success", "message": f"Successfully approved {lifestyle_media_file_name}."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to approve review: {str(e)}"})

def update_regenerated_media_status(
    product_id: str,
    old_lifestyle_media_file_name: str,
    new_lifestyle_media_file_name: str,
    new_gcs_authenticated_file_path: str,
    tool_context: ToolContext = None
) -> str:
    """Updates a status table row with the newly regenerated media details.
    
    Args:
        product_id: The product ID.
        old_lifestyle_media_file_name: The file name of the old (rejected) media.
        new_lifestyle_media_file_name: The file name of the newly generated media.
        new_gcs_authenticated_file_path: The authenticated HTTPS URL to the new file.
        
    Returns:
        A JSON string indicating success or failure of the update operation.
    """
    try:
        client = get_bq_client()
        table_fullname = _ensure_status_table_exists(client)
        
        from datetime import datetime
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        generated_by = tool_context.user_id if tool_context else None

        ext = new_lifestyle_media_file_name.lower().split(".")[-1]
        media_format = ext.upper()
        if ext in ("jpg", "jpeg", "png"):
            media_type = "Image"
        elif ext == "mp4":
            media_type = "Video"
        else:
            media_type = "Unknown"

        query = f"""
            UPDATE `{table_fullname}`
            SET lifestyle_media_file_name = @new_lifestyle_media_file_name,
                gcs_authenticated_file_path = @new_gcs_authenticated_file_path,
                generation_status = 'SUCCESS',
                last_reviewed_date = @now,
                review_status = 'PENDING',
                generation_failure_msg = NULL,
                media_type = @media_type,
                media_format = @media_format,
                generated_by = @generated_by,
                reviewed_by = NULL
            WHERE product_id = @product_id AND lifestyle_media_file_name = @old_lifestyle_media_file_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("new_lifestyle_media_file_name", "STRING", new_lifestyle_media_file_name),
                bigquery.ScalarQueryParameter("new_gcs_authenticated_file_path", "STRING", new_gcs_authenticated_file_path),
                bigquery.ScalarQueryParameter("now", "TIMESTAMP", now_str),
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("old_lifestyle_media_file_name", "STRING", old_lifestyle_media_file_name),
                bigquery.ScalarQueryParameter("media_type", "STRING", media_type),
                bigquery.ScalarQueryParameter("media_format", "STRING", media_format),
                bigquery.ScalarQueryParameter("generated_by", "STRING", generated_by),
            ]
        )
        query_job = client.query(query, job_config=job_config)
        query_job.result() # Wait for completion
        
        return json.dumps({"status": "success", "message": f"Successfully updated regeneration status for product {product_id}."})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to update regeneration status: {str(e)}"})

# Cloud Storage Configuration
gcs_bucket = os.environ.get("GCS_BUCKET", "at_home_product_lifestyle_content")

# Lazy clients
_bq_client = None
_storage_client = None

def get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=project_id, location=bq_location)
    return _bq_client

def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=project_id)
    return _storage_client


def _get_gcs_url(bucket_name: str, blob_name: str) -> str:
    """Generates a signed URL or falls back to authenticated browser URL."""
    try:
        from datetime import timedelta
        bucket = get_storage_client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        # Generate signed URL (valid for 24 hours)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=24),
            method="GET"
        )
        return signed_url
    except Exception as e:
        print(f"Failed to generate signed URL: {e}. Falling back to authenticated browser URL.")
        return f"https://storage.cloud.google.com/{bucket_name}/{blob_name}"

def _get_public_url(bucket_name: str, blob_name: str) -> str:
    """Returns the public (unauthenticated) HTTPS URL for a GCS object.

    Only resolves if the object/bucket grants public read access.
    """
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

def _fetch_bq_rows(product_id: str = None, total_rows: int = 5) -> list:
    """Private helper to query BigQuery catalog with a fallback if Dimensions column is missing."""
    from google.api_core.exceptions import BadRequest

    def run_query(select_dimensions: bool) -> list:
        dim_col = ", Dimensions" if select_dimensions else ""
        if product_id:
            query = f"""
                SELECT `product-id`, `product-name`, primaryCategoryName, `short-description`{dim_col}, cloudinaryProductImages
                FROM `{project_id}.{bq_dataset}.{bq_table}`
                WHERE `product-id` = '{product_id}'
            """
        else:
            query = f"""
                SELECT `product-id`, `product-name`, primaryCategoryName, `short-description`{dim_col}, cloudinaryProductImages
                FROM `{project_id}.{bq_dataset}.{bq_table}`
                LIMIT {total_rows}
            """
        query_job = get_bq_client().query(query)
        return list(query_job.result())

    try:
        # Try querying with Dimensions first
        return [dict(row) for row in run_query(select_dimensions=True)]
    except BadRequest as e:
        if "Dimensions" in str(e):
            print("Dimensions column not found in BigQuery catalog schema. Falling back to query without Dimensions.")
            # Fallback to query without Dimensions, and inject an empty Dimensions key for compatibility
            rows = []
            for row in run_query(select_dimensions=False):
                row_dict = dict(row)
                row_dict["Dimensions"] = ""
                rows.append(row_dict)
            return rows
        raise e

def _upload_to_gcs(bucket_name: str, destination_blob_name: str, data_bytes: bytes, content_type: str = "image/jpeg") -> bool:
    """Private helper to upload generated media to GCS with fallbacks."""
    bucket = get_storage_client().bucket(bucket_name)
    bucket_exists = False
    try:
        bucket_exists = bucket.exists()
    except Exception as e:
        print(f"Error checking if bucket '{bucket_name}' exists: {e}")
        
    if not bucket_exists:
        fallback_bucket_name = "at_home_product_lifestyle_content"
        print(f"Bucket '{bucket_name}' does not exist. Checking fallback bucket '{fallback_bucket_name}'...")
        bucket = get_storage_client().bucket(fallback_bucket_name)
        try:
            if not bucket.exists():
                print(f"Fallback bucket '{fallback_bucket_name}' does not exist. Creating it...")
                bucket = get_storage_client().create_bucket(fallback_bucket_name, project=project_id, location=veo_location)
                print(f"Successfully created bucket '{fallback_bucket_name}'.")
        except Exception as e:
            print(f"Failed to check or create fallback bucket '{fallback_bucket_name}'. Error: {e}")
            return False
        bucket_name = fallback_bucket_name

    # Create default folders for fallback bucket if they don't exist
    if bucket_name == "at_home_product_lifestyle_content":
        for folder in ["product_images/", "product_videos/"]:
            folder_blob = bucket.blob(folder)
            if not folder_blob.exists():
                try:
                    folder_blob.upload_from_string("", content_type="application/x-directory")
                except Exception as e:
                    print(f"Could not create folder '{folder}': {e}")
                    
    # Create product specific folders if they do not exist under product_images or product_videos
    parts = destination_blob_name.split('/')
    if len(parts) > 1:
        product_folder = "/".join(parts[:-1]) + "/"
        product_folder_blob = bucket.blob(product_folder)
        if not product_folder_blob.exists():
            try:
                product_folder_blob.upload_from_string("", content_type="application/x-directory")
            except Exception as e:
                print(f"Could not create product folder '{product_folder}': {e}")
                
    # Now upload the content
    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(data_bytes, content_type=content_type)
        print(f"Successfully uploaded to gs://{bucket_name}/{destination_blob_name}")
        return True
    except Exception as e:
        print(f"Failed to upload to GCS. Error: {e}")
        return False

# ---------------------------------------------------------
# Exposed Agent Tools
# ---------------------------------------------------------

def get_product_details(product_id: str = None, limit: int = 5) -> str:
    """Queries the BigQuery catalog to retrieve product information.

    Args:
        product_id: The unique string product ID (optional). If specified, retrieves details for only this product.
        limit: The maximum number of products to retrieve if product_id is not specified (default 5).

    Returns:
        A JSON-formatted string containing a list of product records, or an error message.
    """
    try:
        rows = _fetch_bq_rows(product_id=product_id, total_rows=limit)
        if not rows:
            return json.dumps({"status": "error", "message": "No products found matching the criteria."})
        
        results = []
        for row in rows:
            # Extract columns safely
            results.append({
                "product_id": row["product-id"],
                "product_name": row["product-name"] or "",
                "primary_category": row["primaryCategoryName"] or "",
                "short_description": row["short-description"] or "",
                "cloudinary_images": row["cloudinaryProductImages"] or ""
            })
            
        return json.dumps({"status": "success", "products": results}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to query catalog. Error: {str(e)}"})


def generate_and_save_lifestyle_image(
    product_id: str,
    additional_instructions: str = "",
    old_lifestyle_media_file_name: Optional[str] = None,
    tool_context: ToolContext = None
) -> str:
    """Generates a high-quality professional lifestyle photography image for a given product ID and saves it to Cloud Storage.

    Args:
        product_id: The unique string product ID.
        additional_instructions: Optional stylistic directions or details to append to the creative prompt.

    Returns:
        A JSON-formatted string containing success status, the GCS path, and authenticated HTTPS link, or a detailed error message.
    """
    from datetime import datetime
    generation_time = datetime.utcnow()
    current_date = generation_time.strftime("%Y%m%d")
    current_time = generation_time.strftime("%H%M%S")
    filename = f"{product_id}-{current_date}-{current_time}.jpg"
    destination_blob = f"product_images/{product_id}/{filename}"

    generated_by = tool_context.user_id if tool_context else None

    def _log_failure(msg: str):
        try:
            update_media_generation_status_result(
                product_id=product_id,
                lifestyle_media_file_name=filename,
                generation_status="FAILURE",
                generation_failure_msg=msg
            )
        except Exception as le:
            print(f"Failed to log failure to BigQuery: {le}")

    try:
        rows = _fetch_bq_rows(product_id=product_id)
        if not rows:
            # If product ID is invalid, log failure directly to database and return
            try:
                log_media_generation_status(
                    product_id=product_id,
                    lifestyle_media_file_name=filename,
                    gcs_authenticated_file_path=None,
                    generation_status="FAILURE",
                    generation_failure_msg=f"Product ID {product_id} not found in BigQuery catalog.",
                    generated_by=generated_by
                )
            except Exception as le:
                print(f"Failed to log catalog failure to BigQuery: {le}")
            return json.dumps({"status": "error", "message": f"Product ID {product_id} not found in BigQuery catalog."})

        # Insert a new record or update the existing rejected record to PENDING
        try:
            start_media_generation_status(
                product_id=product_id,
                filename=filename,
                old_lifestyle_media_file_name=old_lifestyle_media_file_name,
                generated_by=generated_by
            )
        except Exception as se:
            print(f"Failed to record start of media generation to BigQuery: {se}")
        
        row = rows[0]
        product_name = row["product-name"] or ""
        primary_category = row["primaryCategoryName"] or ""
        short_desc = row["short-description"] or ""
        dimensions = row["Dimensions"] or ""

        # Clean description from HTML tags
        clean_desc = re.sub('<[^<]+?>', ' ', short_desc)
        clean_desc = " ".join(clean_desc.split())
        
        # Parse reference image URLs from cloudinaryProductImages (use up to first 3)
        cloudinary_images = row["cloudinaryProductImages"]
        image_urls = []
        if cloudinary_images:
            try:
                images_json = json.loads(cloudinary_images)
                for i in range(1, 4):
                    url = images_json.get(f"image{i}")
                    if url:
                        image_urls.append(url)
            except Exception as e:
                print(f"Error parsing cloudinaryProductImages: {e}")
        if not image_urls:
            msg = f"No valid reference image URL found for product ID {product_id}."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})

        # Download reference images
        image_data_list = []
        for url in image_urls:
            try:
                img_response = requests.get(url)
                img_response.raise_for_status()
                image_data_list.append(img_response.content)
            except Exception as e:
                print(f"Error downloading reference image {url}: {e}")

        if not image_data_list:
            msg = f"Failed to download any reference images for product ID {product_id}."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
        # Initialize standard GenAI Client
        client = genai.Client(vertexai=True, project=project_id, location=image_location)
        
        # Construct Lifestyle Image Prompt
        prompt_text = (
            "Generate a professional, premium lifestyle photography shot of the attached product.\n\n"
            f"Product ID: {product_id}\n\n"
            f"Product name: {product_name}\n\n"
            f"Product Category: {primary_category}\n\n"
            f"Product Description: {clean_desc}\n\n"
            f"Product Dimensions: {dimensions}\n\n"
            "Image generation instructions:\n"
            "The product must be perfectly integrated into a lifestyle setting.\n"
            "Use the provided product dimensions to render the product at a realistic, true-to-life scale "
            "relative to other objects and the surrounding environment.\n"
            "Use the attached reference image(s) to understand the exact product from multiple angles. "
            "The exact product from the reference images must be seamlessly blended into the new environment, "
            "preserving its original details and color. Adapt naturally to the new lighting, cast shadows, perspective, and reflections.\n"
            "Only depict the product from angles and sides that are actually visible in the reference image(s). "
            "If a particular side or angle (e.g., the back or a side view) is not shown in any reference image, do NOT invent, guess, or fabricate it. "
            "Instead, compose the scene so the product is shown only from angles supported by the references, keeping unseen parts out of view or naturally occluded.\n"
            "Make sure the subject is mostly centered in the frame and the shot is either a full shot or a medium full shot.\n"
            "Do not use product labels or alcohol in the scene."
        )
        
        if additional_instructions:
            prompt_text += f"\nAdditional instructions: {additional_instructions}"
            
        # Call Gemini Multimodal Image API (gemini-3.1-flash-image)
        msg_text = types.Part.from_text(text=prompt_text)
        msg_images = [
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            for img_bytes in image_data_list
        ]

        contents = [
            types.Content(
                role="user",
                parts=[msg_text, *msg_images]
            )
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature = 1,
            top_p = 0.95,
            max_output_tokens = 32768,
            response_modalities = ["IMAGE"],
            safety_settings = [types.SafetySetting(
              category="HARM_CATEGORY_HATE_SPEECH",
              threshold="BLOCK_LOW_AND_ABOVE"
            ),types.SafetySetting(
              category="HARM_CATEGORY_DANGEROUS_CONTENT",
              threshold="BLOCK_LOW_AND_ABOVE"
            ),types.SafetySetting(
              category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
              threshold="BLOCK_LOW_AND_ABOVE"
            ),types.SafetySetting(
              category="HARM_CATEGORY_HARASSMENT",
              threshold="BLOCK_LOW_AND_ABOVE"
            )],
            image_config=types.ImageConfig(
              aspect_ratio="1:1",
              image_size="2K",
              output_mime_type="image/jpeg",
            ),
            thinking_config=types.ThinkingConfig(
              thinking_level="MINIMAL",
            ),
        )
        
        print("Calling Gemini Multimodal Image API (gemini-3.1-flash-image)...")
        image_bytes = b""
        for chunk in client.models.generate_content_stream(
            model="gemini-3.1-flash-image",
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if part.inline_data:
                        image_bytes += part.inline_data.data
                        
        if not image_bytes:
            msg = f"Gemini API returned empty image bytes for product ID {product_id}."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})

        # Resize to exact target dimensions (1800x1800 JPEG). The Gemini image API only
        # accepts size presets ("2K") rather than exact pixel dimensions, so we downscale
        # the generated image to the required output size before upload.
        source_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        resized_image = source_image.resize((1800, 1800), Image.LANCZOS)
        output_buffer = io.BytesIO()
        resized_image.save(output_buffer, format="JPEG", quality=95)
        image_bytes = output_buffer.getvalue()
        success = _upload_to_gcs(
            bucket_name=gcs_bucket,
            destination_blob_name=destination_blob,
            data_bytes=image_bytes,
            content_type="image/jpeg"
        )
        
        if success:
            gcs_uri = f"gs://{gcs_bucket}/{destination_blob}"
            http_url = _get_gcs_url(gcs_bucket, destination_blob)
            public_url = _get_public_url(gcs_bucket, destination_blob)

            # Update status to success in BigQuery
            try:
                update_media_generation_status_result(
                    product_id=product_id,
                    lifestyle_media_file_name=filename,
                    generation_status="SUCCESS",
                    gcs_authenticated_file_path=http_url
                )
            except Exception as le:
                print(f"Failed to update success status in BigQuery: {le}")
            return json.dumps({
                "status": "success",
                "gcs_uri": gcs_uri,
                "authenticated_url": http_url,
                "public_url": public_url,
                "media_type": "image",
                "product_id": product_id,
                "product_details": {
                    "product_name": product_name,
                    "primary_category": primary_category,
                    "short_description": clean_desc
                }
            }, indent=2)
        else:
            msg = "Failed to upload the generated image to Cloud Storage."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
            
    except Exception as e:
        msg = f"Error generating lifestyle image for product {product_id}: {str(e)}"
        _log_failure(msg)
        return json.dumps({"status": "error", "message": msg})


def generate_and_save_lifestyle_video(
    product_id: str,
    additional_instructions: str = "",
    old_lifestyle_media_file_name: Optional[str] = None,
    tool_context: ToolContext = None
) -> str:
    """Generates a high-quality professional 8-second lifestyle video shot for a given product ID and saves it to Cloud Storage.

    Args:
        product_id: The unique string product ID.
        additional_instructions: Optional stylistic directions or camera movement details to append to the creative prompt.

    Returns:
        A JSON-formatted string containing success status, the GCS path, and authenticated HTTPS link, or a detailed error message.
    """
    from datetime import datetime
    generation_time = datetime.utcnow()
    current_date = generation_time.strftime("%Y%m%d")
    current_time = generation_time.strftime("%H%M%S")
    filename = f"{product_id}-{current_date}-{current_time}.mp4"
    destination_blob = f"product_videos/{product_id}/{filename}"

    generated_by = tool_context.user_id if tool_context else None

    def _log_failure(msg: str):
        try:
            update_media_generation_status_result(
                product_id=product_id,
                lifestyle_media_file_name=filename,
                generation_status="FAILURE",
                generation_failure_msg=msg
            )
        except Exception as le:
            print(f"Failed to log failure to BigQuery: {le}")

    try:
        rows = _fetch_bq_rows(product_id=product_id)
        if not rows:
            # If product ID is invalid, log failure directly to database and return
            try:
                log_media_generation_status(
                    product_id=product_id,
                    lifestyle_media_file_name=filename,
                    gcs_authenticated_file_path=None,
                    generation_status="FAILURE",
                    generation_failure_msg=f"Product ID {product_id} not found in BigQuery catalog.",
                    generated_by=generated_by
                )
            except Exception as le:
                print(f"Failed to log catalog failure to BigQuery: {le}")
            return json.dumps({"status": "error", "message": f"Product ID {product_id} not found in BigQuery catalog."})

        # Insert a new record or update the existing rejected record to PENDING
        try:
            start_media_generation_status(
                product_id=product_id,
                filename=filename,
                old_lifestyle_media_file_name=old_lifestyle_media_file_name,
                generated_by=generated_by
            )
        except Exception as se:
            print(f"Failed to record start of media generation to BigQuery: {se}")
        
        row = rows[0]
        product_name = row["product-name"] or ""
        primary_category = row["primaryCategoryName"] or ""
        short_desc = row["short-description"] or ""
        dimensions = row["Dimensions"] or ""

        # Clean description
        clean_desc = re.sub('<[^<]+?>', ' ', short_desc)
        clean_desc = " ".join(clean_desc.split())
        
        # Parse reference image URL from cloudinaryProductImages
        cloudinary_images = row["cloudinaryProductImages"]
        image_url = None
        if cloudinary_images:
            try:
                images_json = json.loads(cloudinary_images)
                image_url = images_json.get("image1")
            except Exception as e:
                print(f"Error parsing cloudinaryProductImages: {e}")
                
        if not image_url:
            msg = f"No valid reference image URL found for product ID {product_id}."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
        
        # Download reference image
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        image_data = img_response.content
        
        # Initialize standard GenAI Client
        client = genai.Client(vertexai=True, project=project_id, location=veo_location)
        
        # Construct Video Prompt
        prompt_text = (
            "Generate a professional, premium lifestyle video shot of the attached product.\n\n"
            f"Product ID: {product_id}\n\n"
            f"Product name: {product_name}\n\n"
            f"Product Category: {primary_category}\n\n"
            f"Product Description: {clean_desc}\n\n"
            f"Product Dimensions: {dimensions}\n\n"
            "Video generation instructions:\n"
            "The product must be perfectly integrated into a lifestyle setting.\n"
            "Use the provided product dimensions to render the product at a realistic, true-to-life scale "
            "relative to other objects and the surrounding environment.\n"
            "The exact product from the reference image must be seamlessly blended into the new environment, preserving its original details and color. Adapt naturally to the new lighting, cast shadows, perspective, and reflections."
        )
        if additional_instructions:
            prompt_text += f"\n\nAdditional video generation instructions: {additional_instructions}"
            
        # Generate Video Config
        config = types.GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            duration_seconds=8,
            person_generation="allow_all",
            generate_audio=False,
            resolution="1080p",
            seed=0,
        )
        
        # Construct Video Source
        source = types.GenerateVideosSource(
            prompt=prompt_text,
            image=types.Image(
                image_bytes=image_data,
                mime_type="image/jpeg",
            )
        )
        
        print("Calling Gemini Video Generation API (veo-3.1-fast-generate-001)...")
        operation = client.models.generate_videos(
            model="veo-3.1-fast-generate-001",
            source=source,
            config=config
        )
        
        while not operation.done:
            print("Waiting for video generation to complete...")
            time.sleep(15)
            operation = client.operations.get(operation)
            
        if not operation.response or not operation.response.generated_videos:
            err_msg = ""
            if hasattr(operation, 'error') and operation.error:
                err_msg = f" Operation error: {operation.error}"
            msg = f"Veo model returned no generated videos.{err_msg}"
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
            
        generated_video = operation.response.generated_videos[0]
        video_bytes = generated_video.video.video_bytes
        
        # Download if URI returned instead of direct bytes
        if not video_bytes and generated_video.video.uri:
            gcs_uri = generated_video.video.uri
            print(f"Video URI returned: {gcs_uri}. Downloading bytes...")
            gcs_match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
            if gcs_match:
                src_bucket_name = gcs_match.group(1)
                src_blob_name = gcs_match.group(2)
                try:
                    src_bucket = get_storage_client().bucket(src_bucket_name)
                    src_blob = src_bucket.blob(src_blob_name)
                    video_bytes = src_blob.download_as_bytes()
                except Exception as e:
                    msg = f"Failed to download video bytes from generated source bucket. Details: {str(e)}"
                    _log_failure(msg)
                    return json.dumps({"status": "error", "message": msg})
            else:
                msg = f"Unexpected video URI format: {gcs_uri}"
                _log_failure(msg)
                return json.dumps({"status": "error", "message": msg})
        elif not video_bytes:
            msg = "No video bytes or GCS URI returned in Veo model response."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
            
        success = _upload_to_gcs(
            bucket_name=gcs_bucket,
            destination_blob_name=destination_blob,
            data_bytes=video_bytes,
            content_type="video/mp4"
        )
        
        if success:
            gcs_uri = f"gs://{gcs_bucket}/{destination_blob}"
            http_url = _get_gcs_url(gcs_bucket, destination_blob)
            public_url = _get_public_url(gcs_bucket, destination_blob)

            # Update status to success in BigQuery
            try:
                update_media_generation_status_result(
                    product_id=product_id,
                    lifestyle_media_file_name=filename,
                    generation_status="SUCCESS",
                    gcs_authenticated_file_path=http_url
                )
            except Exception as le:
                print(f"Failed to update success status in BigQuery: {le}")
            return json.dumps({
                "status": "success",
                "gcs_uri": gcs_uri,
                "authenticated_url": http_url,
                "public_url": public_url,
                "media_type": "video",
                "product_id": product_id,
                "product_details": {
                    "product_name": product_name,
                    "primary_category": primary_category,
                    "short_description": clean_desc
                }
            }, indent=2)
        else:
            msg = "Failed to upload the generated video to Cloud Storage."
            _log_failure(msg)
            return json.dumps({"status": "error", "message": msg})
            
    except Exception as e:
        msg = f"Error generating lifestyle video for product {product_id}: {str(e)}"
        _log_failure(msg)
        return json.dumps({"status": "error", "message": msg})
