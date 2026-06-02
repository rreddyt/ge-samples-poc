import os
import requests
import json
import re
from datetime import datetime
from google.cloud import bigquery
from google.cloud import storage
from google import genai
from google.genai import types

def load_dotenv(dotenv_path: str):
    """Loads environment variables from a .env file if it exists."""
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines or comments
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Remove optional surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key:
                os.environ[key] = val

# Load environment variables from .env file in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

# Disable client certificate checks to avoid mTLS helper segfault issues in this environment
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

def get_bq_rows(project_id: str, dataset: str, table: str, product_id: str = None, total_rows: int = 5):
    """Queries BigQuery table for product information."""
    bq_client = bigquery.Client(project=project_id, location="us-central1")
    
    if product_id:
        prod_id_str = product_id.strip()
        print(f"Querying BigQuery table for single product ID '{prod_id_str}'...")
        query = f"""
            SELECT `product-id`, `product-name`, primaryCategoryName, `short-description`, cloudinaryProductImages
            FROM `{project_id}.{dataset}.{table}`
            WHERE `product-id` = '{prod_id_str}'
        """
    else:
        print(f"Querying BigQuery table for first {total_rows} products...")
        query = f"""
            SELECT `product-id`, `product-name`, primaryCategoryName, `short-description`, cloudinaryProductImages
            FROM `{project_id}.{dataset}.{table}`
            LIMIT {total_rows}
        """
        
    try:
        query_job = bq_client.query(query)
        results = query_job.result()
        return list(results)
    except Exception as e:
        print(f"Failed to query BigQuery table. Error: {e}")
        raise e

def generate_lifestyle_image(client: genai.Client, image_data: bytes, prompt_text: str) -> bytes:
    """Generates a lifestyle image using gemini-3.1-flash-image with the given reference image and prompt."""
    # Prepare multimodal parts
    msg_text = types.Part.from_text(text=prompt_text)
    msg_image = types.Part.from_bytes(
        data=image_data,
        mime_type="image/jpeg",
    )
    
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
        safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_LOW_AND_ABOVE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_LOW_AND_ABOVE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_LOW_AND_ABOVE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_LOW_AND_ABOVE"
            )
        ],
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
                elif part.text:
                    print(part.text, end="")
                    
    return image_bytes

def upload_to_gcs(bucket_name: str, destination_blob_name: str, data_bytes: bytes, project_id: str, location: str = "us-central1", content_type: str = "image/jpeg") -> bool:
    """Uploads bytes to a Google Cloud Storage bucket, creating a fallback bucket and folder structure if needed."""
    storage_client = storage.Client()
    
    # Check if the target bucket exists
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
                print(f"Fallback bucket '{fallback_bucket_name}' does not exist. Creating it in project '{project_id}'...")
                bucket = storage_client.create_bucket(fallback_bucket_name, project=project_id, location=location)
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
                    print(f"Created folder '{folder}' in bucket '{bucket_name}'.")
                except Exception as e:
                    print(f"Could not create folder '{folder}'. Error: {e}")
                    
    # Create product specific folders if they do not exist under product_images or product_videos
    parts = destination_blob_name.split('/')
    if len(parts) > 1:
        product_folder = "/".join(parts[:-1]) + "/"
        product_folder_blob = bucket.blob(product_folder)
        if not product_folder_blob.exists():
            try:
                product_folder_blob.upload_from_string("", content_type="application/x-directory")
                print(f"Created product folder '{product_folder}' in bucket '{bucket_name}'.")
            except Exception as e:
                print(f"Could not create product folder '{product_folder}'. Error: {e}")
                
    # Now upload the content
    print(f"Uploading to GCS bucket '{bucket_name}' as '{destination_blob_name}'...")
    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(data_bytes, content_type=content_type)
        print(f"Successfully uploaded to gs://{bucket_name}/{destination_blob_name}")
        return True
    except Exception as e:
        print(f"Failed to upload to GCS. Error: {e}")
        return False

if __name__ == "__main__":
    # Enable client certificate checks avoidance
    os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

    # 1. Load inputs from environment variables with defaults (except PRODUCT_ID and TOTAL_ROWS_ENV)
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT", "vr-payg-nonprod")
    BQ_DATASET = os.environ.get("BQ_DATASET", "at_home_dataset")
    BQ_TABLE = os.environ.get("BQ_TABLE", "product_main_catalog")
    GCS_BUCKET = os.environ.get("GCS_BUCKET", "at_home_product_lifestyle_images")
    LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
    
    print("Select lifestyle generation mode:")
    print("1. Generate lifestyle image for a single product by PRODUCT_ID")
    print("2. Generate lifestyle video for a given product by PRODUCT_ID")
    print("3. Generate lifestyle image for the first N rows of the product_main_catalog table")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    while choice not in ["1", "2", "3"]:
        print("Invalid choice. Please enter 1, 2, or 3.")
        choice = input("Enter choice (1, 2, or 3): ").strip()
        
    PRODUCT_ID = None
    TOTAL_ROWS_ENV = None
    additional_instructions = ""
    
    if choice in ["1", "2"]:
        while not PRODUCT_ID:
            input_val = input("Enter PRODUCT_ID: ").strip()
            if not input_val:
                print("PRODUCT_ID is required for this mode.")
            else:
                PRODUCT_ID = input_val
        if choice == "1":
            additional_instructions = input("Enter additional image generation instructions (optional, press Enter to skip): ").strip()
        else:
            additional_instructions = input("Enter additional video generation instructions (optional, press Enter to skip): ").strip()
    else:
        total_rows_input = input("Enter number of rows to process (default 5): ").strip()
        if not total_rows_input:
            TOTAL_ROWS_ENV = "5"
        else:
            while not total_rows_input.isdigit() or int(total_rows_input) <= 0:
                print("Please enter a positive integer.")
                total_rows_input = input("Enter number of rows to process (default 5): ").strip()
                if not total_rows_input:
                    total_rows_input = "5"
                    break
            TOTAL_ROWS_ENV = total_rows_input
            
    print(f"--- Configuration ---")
    print(f"GCP Project ID: {PROJECT_ID}")
    print(f"BigQuery Dataset: {BQ_DATASET}")
    print(f"BigQuery Table: {BQ_TABLE}")
    print(f"Cloud Storage Bucket: {GCS_BUCKET}")
    print(f"GCP Location: {LOCATION}")
    if choice == "1":
        print(f"Mode: Single Product Image Generation ({PRODUCT_ID})")
    elif choice == "2":
        print(f"Mode: Single Product Video Generation ({PRODUCT_ID})")
    else:
        print(f"Mode: Batch Image Generation (TOTAL_ROWS: {TOTAL_ROWS_ENV})")
    print(f"---------------------\n")
    
    # 2. Fetch data from BigQuery
    try:
        rows = get_bq_rows(
            project_id=PROJECT_ID,
            dataset=BQ_DATASET,
            table=BQ_TABLE,
            product_id=PRODUCT_ID,
            total_rows=int(TOTAL_ROWS_ENV) if TOTAL_ROWS_ENV else 5
        )
    except ValueError:
        print(f"Error: Invalid TOTAL_ROWS value '{TOTAL_ROWS_ENV}'.")
        exit(1)
    except Exception as e:
        print(f"Query execution failed. Error: {e}")
        exit(1)
        
    if not rows:
        print("No rows found matching the query.")
        exit(0)
        
    # 3. Initialize GenAI client
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"Failed to initialize GenAI client. Error: {e}")
        exit(1)
        
    # 4. Loop through products
    count = 0
    for row in rows:
        # Convert columns
        # Row is a Row object, which supports key-based access
        product_id = row["product-id"]
        product_name = row["product-name"] or ""
        primary_category = row["primaryCategoryName"] or ""
        short_desc = row["short-description"]
        
        print(f"\n--- Processing product {count + 1}/{len(rows)} ---")
        print(f"Product ID: {product_id}")
        print(f"Product Name: {product_name}")
        
        # Clean description
        if short_desc:
            clean_desc = re.sub('<[^<]+?>', ' ', short_desc)
            clean_desc = " ".join(clean_desc.split())
        else:
            clean_desc = ""
            
        # Parse reference image url
        cloudinary_images = row["cloudinaryProductImages"]
        image_url = None
        if cloudinary_images:
            try:
                images_json = json.loads(cloudinary_images)
                image_url = images_json.get("image1")
            except Exception as e:
                print(f"Error parsing cloudinaryProductImages for product {product_id}: {e}")
                
        if not image_url:
            print(f"Skipping product {product_id} - No reference image URL found.")
            continue
            
        # Download reference image
        print(f"Downloading reference image from {image_url}...")
        try:
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            image_data = img_response.content
        except Exception as e:
            print(f"Failed to download reference image for product {product_id}. Error: {e}")
            continue
            
        if choice == "2":
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
            video_config = types.GenerateVideosConfig(
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
            try:
                operation = client.models.generate_videos(
                    model="veo-3.1-fast-generate-001",
                    source=source,
                    config=video_config
                )
                
                import time
                while not operation.done:
                    print("Waiting for video generation to complete...")
                    time.sleep(15)
                    operation = client.operations.get(operation)
                    
                if not operation.response or not operation.response.generated_videos:
                    print(f"Failed to generate lifestyle video for product {product_id}. No video returned.")
                    if hasattr(operation, 'error') and operation.error:
                        print(f"Operation error: {operation.error}")
                    continue
                    
                generated_video = operation.response.generated_videos[0]
                video_bytes = generated_video.video.video_bytes
                
                if not video_bytes and generated_video.video.uri:
                    gcs_uri = generated_video.video.uri
                    print(f"Video URI returned: {gcs_uri}. Downloading bytes from GCS...")
                    import re
                    gcs_match = re.match(r"gs://([^/]+)/(.+)", gcs_uri)
                    if gcs_match:
                        src_bucket_name = gcs_match.group(1)
                        src_blob_name = gcs_match.group(2)
                        try:
                            storage_client = storage.Client()
                            src_bucket = storage_client.bucket(src_bucket_name)
                            src_blob = src_bucket.blob(src_blob_name)
                            video_bytes = src_blob.download_as_bytes()
                        except Exception as e:
                            print(f"Failed to download video bytes from source GCS bucket. Error: {e}")
                            continue
                    else:
                        print(f"Unexpected video URI format: {gcs_uri}")
                        continue
                elif not video_bytes:
                    print("No video bytes or GCS URI returned in the response.")
                    continue
                else:
                    print("Retrieved video bytes directly from model response.")
            except Exception as e:
                print(f"Failed to generate lifestyle video for product {product_id}. Error: {e}")
                continue
                
            if not video_bytes:
                print(f"Failed to download lifestyle video for product {product_id}. No video bytes returned.")
                continue
                
            # Save to GCS
            now = datetime.now()
            current_date = now.strftime("%Y%m%d")
            current_time = now.strftime("%H%M%S")
            filename = f"{product_id}-{current_date}-{current_time}.mp4"
            destination_blob = f"product_videos/{product_id}/{filename}"
            
            success = upload_to_gcs(
                bucket_name=GCS_BUCKET,
                destination_blob_name=destination_blob,
                data_bytes=video_bytes,
                project_id=PROJECT_ID,
                location=LOCATION,
                content_type="video/mp4"
            )
            if success:
                count += 1
        else:
            # Construct Image Prompt
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
                
            # Generate Lifestyle Image
            try:
                generated_bytes = generate_lifestyle_image(
                    client=client,
                    image_data=image_data,
                    prompt_text=prompt_text
                )
            except Exception as e:
                print(f"Failed to generate lifestyle image for product {product_id}. Error: {e}")
                continue
                
            if not generated_bytes:
                print(f"Failed to generate lifestyle image for product {product_id}. No image bytes returned.")
                continue
                
            # Save to GCS
            now = datetime.now()
            current_date = now.strftime("%Y%m%d")
            current_time = now.strftime("%H%M%S")
            filename = f"{product_id}-{current_date}-{current_time}.jpg"
            destination_blob = f"product_images/{product_id}/{filename}"
            
            success = upload_to_gcs(
                bucket_name=GCS_BUCKET,
                destination_blob_name=destination_blob,
                data_bytes=generated_bytes,
                project_id=PROJECT_ID,
                location=LOCATION,
                content_type="image/jpeg"
            )
            if success:
                count += 1
            
    print(f"\nDone! Successfully processed and saved {count} product lifestyle content items to GCS.")