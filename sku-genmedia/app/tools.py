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
import time
import json
import re
import requests
from datetime import datetime

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

# Retrieve configurations from environment
_, project_default = google.auth.default()
project_id = os.environ.get("GCP_PROJECT_ID", project_default)
gemini_location = os.environ.get("GEMINI_LOCATION", os.environ.get("GCP_LOCATION", "global"))
veo_location = os.environ.get("VEO_LOCATION", "us-central1")

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# BigQuery Configuration
bq_dataset = os.environ.get("BQ_DATASET", "at_home_dataset")
bq_table = os.environ.get("BQ_TABLE", "product_main_catalog")

# Cloud Storage Configuration
gcs_bucket = os.environ.get("GCS_BUCKET", "at_home_product_lifestyle_content")

# Initialize clients
bq_client = bigquery.Client(project=project_id, location="us-central1")
storage_client = storage.Client(project=project_id)

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def _fetch_bq_rows(product_id: int = None, total_rows: int = 5) -> list:
    """Private helper to query BigQuery catalog."""
    if product_id:
        query = f"""
            SELECT `product-id`, `product-name`, primaryCategoryName, `long-description`, cloudinaryProductImages
            FROM `{project_id}.{bq_dataset}.{bq_table}`
            WHERE `product-id` = {product_id}
        """
    else:
        query = f"""
            SELECT `product-id`, `product-name`, primaryCategoryName, `long-description`, cloudinaryProductImages
            FROM `{project_id}.{bq_dataset}.{bq_table}`
            LIMIT {total_rows}
        """
    query_job = bq_client.query(query)
    return list(query_job.result())

def _upload_to_gcs(bucket_name: str, destination_blob_name: str, data_bytes: bytes, content_type: str = "image/jpeg") -> bool:
    """Private helper to upload generated media to GCS with fallbacks."""
    bucket = storage_client.bucket(bucket_name)
    bucket_exists = False
    try:
        bucket_exists = bucket.exists()
    except Exception as e:
        print(f"Error checking if bucket '{bucket_name}' exists: {e}")
        
    if not bucket_exists:
        fallback_bucket_name = "at_home_product_lifestyle_content"
        print(f"Bucket '{bucket_name}' does not exist. Checking fallback bucket '{fallback_bucket_name}'...")
        bucket = storage_client.bucket(fallback_bucket_name)
        try:
            if not bucket.exists():
                print(f"Fallback bucket '{fallback_bucket_name}' does not exist. Creating it...")
                bucket = storage_client.create_bucket(fallback_bucket_name, project=project_id, location=veo_location)
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

def get_product_details(product_id: int = None, limit: int = 5) -> str:
    """Queries the BigQuery catalog to retrieve product information.

    Args:
        product_id: The unique integer product ID (optional). If specified, retrieves details for only this product.
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
                "long_description": row["long-description"] or "",
                "cloudinary_images": row["cloudinaryProductImages"] or ""
            })
            
        return json.dumps({"status": "success", "products": results}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to query catalog. Error: {str(e)}"})


def generate_and_save_lifestyle_image(product_id: int, additional_instructions: str = "") -> str:
    """Generates a high-quality professional lifestyle photography image for a given product ID and saves it to Cloud Storage.

    Args:
        product_id: The unique integer product ID.
        additional_instructions: Optional stylistic directions or details to append to the creative prompt.

    Returns:
        A success message containing the GCS path where the image is stored, or a detailed error message.
    """
    try:
        rows = _fetch_bq_rows(product_id=product_id)
        if not rows:
            return f"Error: Product ID {product_id} not found in BigQuery catalog."
        
        row = rows[0]
        product_name = row["product-name"] or ""
        primary_category = row["primaryCategoryName"] or ""
        long_desc = row["long-description"] or ""
        
        # Clean description from HTML tags
        clean_desc = re.sub('<[^<]+?>', ' ', long_desc)
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
            return f"Error: No valid reference image URL found for product ID {product_id}."
        
        # Download reference image
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        image_data = img_response.content
        
        # Initialize standard GenAI Client
        client = genai.Client(vertexai=True, project=project_id, location=gemini_location)
        
        # Construct Lifestyle Image Prompt
        prompt_text = (
            "Generate a professional, premium lifestyle photography shot of the attached product.\n\n"
            f"Product ID: {product_id}\n\n"
            f"Product name: {product_name}\n\n"
            f"Product Category: {primary_category}\n\n"
            f"Product Description: {clean_desc}\n\n"
            "Image generation instructions:\n"
            "The product must be perfectly integrated into a lifestyle setting.\n"
            "The exact product from the reference image must be seamlessly blended into the new environment, "
            "preserving its original details and color. Adapt naturally to the new lighting, cast shadows, perspective, and reflections."
        )
        
        if additional_instructions:
            prompt_text += f"\nAdditional instructions: {additional_instructions}"
            
        # Call Gemini Multimodal Image API (gemini-3.1-flash-image)
        msg_text = types.Part.from_text(text=prompt_text)
        msg_image = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        
        contents = [
            types.Content(
                role="user",
                parts=[msg_text, msg_image]
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
            return f"Error: Gemini API returned empty image bytes for product ID {product_id}."
            
        # Save to GCS
        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        current_time = now.strftime("%H%M%S")
        filename = f"{product_id}-{current_date}-{current_time}.jpg"
        destination_blob = f"product_images/{product_id}/{filename}"
        
        success = _upload_to_gcs(
            bucket_name=gcs_bucket,
            destination_blob_name=destination_blob,
            data_bytes=image_bytes,
            content_type="image/jpeg"
        )
        
        if success:
            return f"Success: Generated lifestyle image and uploaded to gs://{gcs_bucket}/{destination_blob}"
        else:
            return "Error: Failed to upload the generated image to Cloud Storage."
            
    except Exception as e:
        return f"Error generating lifestyle image for product {product_id}: {str(e)}"


def generate_and_save_lifestyle_video(product_id: int, additional_instructions: str = "") -> str:
    """Generates a high-quality professional 8-second lifestyle video shot for a given product ID and saves it to Cloud Storage.

    Args:
        product_id: The unique integer product ID.
        additional_instructions: Optional stylistic directions or camera movement details to append to the creative prompt.

    Returns:
        A success message containing the GCS path where the video is stored, or a detailed error message.
    """
    try:
        rows = _fetch_bq_rows(product_id=product_id)
        if not rows:
            return f"Error: Product ID {product_id} not found in BigQuery catalog."
        
        row = rows[0]
        product_name = row["product-name"] or ""
        primary_category = row["primaryCategoryName"] or ""
        long_desc = row["long-description"] or ""
        
        # Clean description
        clean_desc = re.sub('<[^<]+?>', ' ', long_desc)
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
            return f"Error: No valid reference image URL found for product ID {product_id}."
        
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
            "Video generation instructions:\n"
            "The product must be perfectly integrated into a lifestyle setting.\n"
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
            return f"Error: Veo model returned no generated videos.{err_msg}"
            
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
                    src_bucket = storage_client.bucket(src_bucket_name)
                    src_blob = src_bucket.blob(src_blob_name)
                    video_bytes = src_blob.download_as_bytes()
                except Exception as e:
                    return f"Error: Failed to download video bytes from generated source bucket. Details: {str(e)}"
            else:
                return f"Error: Unexpected video URI format: {gcs_uri}"
        elif not video_bytes:
            return "Error: No video bytes or GCS URI returned in Veo model response."
            
        # Save to GCS
        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        current_time = now.strftime("%H%M%S")
        filename = f"{product_id}-{current_date}-{current_time}.mp4"
        destination_blob = f"product_videos/{product_id}/{filename}"
        
        success = _upload_to_gcs(
            bucket_name=gcs_bucket,
            destination_blob_name=destination_blob,
            data_bytes=video_bytes,
            content_type="video/mp4"
        )
        
        if success:
            return f"Success: Generated lifestyle video and uploaded to gs://{gcs_bucket}/{destination_blob}"
        else:
            return "Error: Failed to upload the generated video to Cloud Storage."
            
    except Exception as e:
        return f"Error generating lifestyle video for product {product_id}: {str(e)}"
