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
import sys
import json
from datetime import datetime

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
from google.api_core.exceptions import NotFound
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types
from pydantic import BaseModel

class ProductDetail(BaseModel):
    product_id: str
    product_name: str
    short_description: str
    primaryCategoryName: str
    dimensions: str

class MockCatalog(BaseModel):
    products: list[ProductDetail]

def create_dummy_png(color: str) -> bytes:
    """Generates a valid 100x100 PNG image of a solid color as a byte string."""
    try:
        img = Image.new("RGB", (100, 100), color=color)
        byte_arr = BytesIO()
        img.save(byte_arr, format='PNG')
        return byte_arr.getvalue()
    except Exception as e:
        print(f"Warning: Failed to generate real PNG with color '{color}', using basic fallback. Error: {e}")
        # 1-pixel transparent png fallback
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

def generate_mock_catalog_with_gemini() -> list[dict]:
    """Uses Gemini to generate mock product details in a structured format."""
    print("\n🤖 Generating mock product details using Gemini (gemini-2.5-flash)...")
    try:
        client = genai.Client()
        
        prompt = """
        Generate exactly 4 highly descriptive mock retail product catalog records.
        They must be for a premium retail store in the categories: 'Pillows', 'Furniture', or 'Lighting'.
        For each product, provide:
        - A unique product_id like SKU-XXXXX (where X is a digit)
        - An official product_name suitable for a high-end store
        - A detailed short_description (2-3 sentences) detailing its material, color, visual style, and traits
        - Its primaryCategoryName (must be either 'Pillows', 'Furniture', or 'Lighting')
        - Its physical dimensions (e.g., '18 in x 18 in x 6 in' for a pillow, '30 in x 36 in x 72 in' for furniture)
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MockCatalog,
            ),
        )
        
        catalog_data = json.loads(response.text)
        products = catalog_data.get("products", [])
        if products:
            print(f"✓ Successfully generated {len(products)} mock products via Gemini!")
            return [
                {
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "short_description": p["short_description"],
                    "primaryCategoryName": p["primaryCategoryName"],
                    "dimensions": p["dimensions"]
                }
                for p in products
            ]
    except Exception as e:
        print(f"⚠️ Failed to generate mock products via Gemini. Error: {e}")
    
    # Fallback to standard high-quality mock products
    print("💡 Falling back to default sample product catalog...")
    return [
        {
            "product_id": "124400264",
            "product_name": "Boho Chic Tufted Throw Pillow",
            "short_description": "A gorgeous, cream-colored woven cotton throw pillow with elegant hand-knotted tassels. Perfect for adding texture and warmth to your boho-chic living room sofa.",
            "primaryCategoryName": "Pillows",
            "dimensions": "18 in x 18 in x 6 in"
        },
        {
            "product_id": "124400265",
            "product_name": "Minimalist Oakwood Bedside Nightstand",
            "short_description": "Sleek, natural oak bedside table with one drawer and minimalist matte black metal legs. Brings a clean Scandinavian design style to your bedroom.",
            "primaryCategoryName": "Furniture",
            "dimensions": "20 in x 18 in x 24 in"
        },
        {
            "product_id": "124400266",
            "product_name": "Emerald Green Velvet Accent Armchair",
            "short_description": "Luxurious deep emerald green velvet armchair with padded armrests and elegant tapered brass gold legs. Adds mid-century modern sophistication.",
            "primaryCategoryName": "Furniture",
            "dimensions": "32 in x 30 in x 35 in"
        },
        {
            "product_id": "124400267",
            "product_name": "Industrial Matte Black Tripod Floor Lamp",
            "short_description": "Sleek matte black metal tripod floor lamp featuring a vintage amber Edison bulb. Creates warm, comfortable, ambient lighting for any modern reading nook.",
            "primaryCategoryName": "Lighting",
            "dimensions": "15 in x 15 in x 65 in"
        }
    ]

def generate_mock_image_with_imagen(product_name: str, angle: str) -> bytes | None:
    """Generates a professional studio product image using Imagen 3."""
    print(f"    🎨 Generating real mock image via Imagen 3 for '{product_name}' ({angle} view)...")
    try:
        client = genai.Client()
        prompt = f"A professional studio product shot of '{product_name}', {angle} view, clean solid white minimalist background, studio lighting, highly detailed, commercial product photography style."
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:3",
                person_generation="DONT_ALLOW",
                output_mime_type="image/png",
            )
        )
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
    except Exception as e:
        print(f"    ⚠️ Imagen generation failed for '{product_name}' ({angle} view): {e}")
    return None

def setup_resources():
    """Provision BigQuery dataset/table, create GCS bucket, and populate sample product data."""
    
    # 1. Determine GCP configuration from environment or default context
    _, project_default = google.auth.default()
    project_id = os.environ.get("GCP_PROJECT_ID", project_default)
    location = os.environ.get("BQ_LOCATION", os.environ.get("GCP_LOCATION", "us-central1"))
    
    bq_dataset = os.environ.get("BQ_DATASET", "at_home_dataset")
    bq_catalog_table = os.environ.get("BQ_TABLE", "product_main_catalog")
    
    catalog_table_id = f"{project_id}.{bq_dataset}.{bq_catalog_table}"
    
    # Bucket name must be globally unique
    bucket_name = os.environ.get("GCS_BUCKET", f"vr-product-lifestyle-content-{project_id}")

    print("=" * 80)
    print(f"🛠️  STARTING GCP PROVISIONING SCRIPT (Product Media Agent)")
    print(f"   GCP Project ID:    {project_id}")
    print(f"   BigQuery Dataset:  {bq_dataset}")
    print(f"   BigQuery Table:    {bq_catalog_table}")
    print(f"   GCS Bucket:        {bucket_name}")
    print(f"   Region/Location:   {location}")
    print("=" * 80)

    # Initialize clients
    bq_client = bigquery.Client(project=project_id, location=location)
    storage_client = storage.Client(project=project_id)

    # --------------------------------------------------------------------------
    # 2. Provision Cloud Storage Bucket
    # --------------------------------------------------------------------------
    print(f"\nProvisioning Cloud Storage bucket '{bucket_name}'...")
    bucket = storage_client.lookup_bucket(bucket_name)
    
    if bucket:
        print(f"✓ Storage Bucket '{bucket_name}' already exists.")
    else:
        print(f"Bucket '{bucket_name}' not found. Creating it...")
        try:
            bucket = storage_client.create_bucket(bucket_name, location=location)
            print(f"🎉 Successfully created Storage Bucket '{bucket_name}' in location '{location}'.")
        except Exception as bucket_error:
            print(f"❌ Failed to create Storage Bucket '{bucket_name}': {bucket_error}")
            return

    # Ensure lifestyle_images/ and product_videos/ folders exist in the bucket
    try:
        for folder in ["lifestyle_images/", "product_videos/", "product_images/"]:
            keep_blob = bucket.blob(f"{folder}.keep")
            keep_blob.upload_from_string(
                f"Placeholder keep file to instantiate folder '{folder}'.",
                content_type="text/plain"
            )
        print("✓ Verified GCS media folder structures.")
    except Exception as folder_error:
        print(f"❌ Error creating GCS folders: {folder_error}")

    # --------------------------------------------------------------------------
    # 3. Provision BigQuery Dataset & Catalog Table
    # --------------------------------------------------------------------------
    dataset_ref = bigquery.DatasetReference(project_id, bq_dataset)
    
    try:
        bq_client.get_dataset(dataset_ref)
        print(f"\n✓ BigQuery Dataset '{bq_dataset}' already exists.")
    except NotFound:
        print(f"\nDataset '{bq_dataset}' not found. Creating it...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        bq_client.create_dataset(dataset)
        print(f"🎉 Successfully created BigQuery Dataset '{bq_dataset}'.")

    # Create Catalog Table (Drop first to refresh schema)
    catalog_table_ref = bigquery.TableReference(dataset_ref, bq_catalog_table)
    try:
        bq_client.delete_table(catalog_table_ref)
        print(f"ℹ Deleted old BigQuery catalog table to refresh schema.")
    except NotFound:
        pass

    print(f"Creating table '{bq_catalog_table}' with the correct schema...")
    schema = [
        bigquery.SchemaField("product-id", "STRING", mode="REQUIRED", description="Unique product catalog identifier"),
        bigquery.SchemaField("product-name", "STRING", mode="REQUIRED", description="Official product name"),
        bigquery.SchemaField("primaryCategoryName", "STRING", description="Official product category"),
        bigquery.SchemaField("short-description", "STRING", description="Detailed marketing description"),
        bigquery.SchemaField("Dimensions", "STRING", description="Physical dimensions of the product"),
        bigquery.SchemaField("cloudinaryProductImages", "STRING", description="JSON string containing reference image URLs"),
    ]
    table = bigquery.Table(catalog_table_ref, schema=schema)
    bq_client.create_table(table)
    print(f"🎉 Successfully created BigQuery Catalog Table '{bq_catalog_table}'.")

    # --------------------------------------------------------------------------
    # 4. Generate Mock Products, Upload 360 images, and Populate BigQuery
    # --------------------------------------------------------------------------
    print(f"\nGenerating sample product catalog and uploading reference images to GCS...")
    
    # Dynamically generate catalog using Gemini or fallback
    sample_products_raw = generate_mock_catalog_with_gemini()
    
    angles = ["front", "side", "back"]
    color_map = {"front": "lightgrey", "side": "grey", "back": "darkgrey"}
    
    sample_products = []
    
    for prod in sample_products_raw:
        product_id = prod["product_id"]
        name = prod["product_name"]
        print(f"\n  Processing product '{name}' (ID: {product_id})...")
        
        image_urls = {}
        for i, angle in enumerate(angles, start=1):
            blob_name = f"products/{product_id}/{angle}.png"
            
            # Try to generate a real product image via Imagen, fallback to color PNG
            png_bytes = generate_mock_image_with_imagen(name, angle)
            if not png_bytes:
                print(f"    ℹ Using solid color fallback PNG for '{name}' ({angle} view)")
                png_bytes = create_dummy_png(color_map[angle])
                
            try:
                blob = bucket.blob(blob_name)
                blob.upload_from_string(png_bytes, content_type="image/png")
                # Make the blob publicly readable so the agent's tools can download it via HTTP
                try:
                    blob.make_public()
                    public_url = blob.public_url
                except Exception:
                    # If make_public fails (e.g. bucket has uniform bucket-level access enabled),
                    # use the standard storage.googleapis.com URL
                    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
                
                image_urls[f"image{i}"] = public_url
                print(f"    ✓ Uploaded {angle} view to GCS: {public_url}")
            except Exception as upload_err:
                print(f"    ❌ Failed uploading {blob_name} to GCS: {upload_err}")
                
        # Construct the BQ row matching the exact schema
        sample_products.append({
            "product-id": product_id,
            "product-name": name,
            "primaryCategoryName": prod["primaryCategoryName"],
            "short-description": prod["short_description"],
            "Dimensions": prod["dimensions"],
            "cloudinaryProductImages": json.dumps(image_urls)
        })

    # Insert rows into BigQuery
    print(f"\nInserting mock product rows into BigQuery table '{bq_catalog_table}'...")
    try:
        errors = bq_client.insert_rows_json(catalog_table_id, sample_products)
        if not errors:
            print(f"🎉 Successfully loaded {len(sample_products)} products into BigQuery!")
        else:
            print(f"❌ Errors inserting sample products: {errors}")
            sys.exit(1)
    except Exception as insert_error:
        print(f"❌ Failed to insert products data: {insert_error}")
        sys.exit(1)
        
    print("\n🏁 GCP Resources Setup Script completed successfully!")
    print("=" * 80)
    print("\n👉 Next steps:")
    print("   1. Check your .env file and ensure GCS_BUCKET matches:")
    print(f"      GCS_BUCKET={bucket_name}")
    print("   2. Run the agent locally using: agents-cli playground")
    print("=" * 80)

if __name__ == "__main__":
    setup_resources()
