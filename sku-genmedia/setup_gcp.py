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
    sku: str
    name: str
    description: str
    category: str

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
        - A unique SKU like SKU-XXXXX (where X is a digit)
        - An official product name suitable for a high-end store
        - A detailed description (2-3 sentences) detailing its material, color, visual style, and traits
        - Its category (must be either 'Pillows', 'Furniture', or 'Lighting')
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
                    "sku": p["sku"],
                    "name": p["name"],
                    "description": p["description"],
                    "category": p["category"]
                }
                for p in products
            ]
    except Exception as e:
        print(f"⚠️ Failed to generate mock products via Gemini. Error: {e}")
    
    # Fallback to standard high-quality mock products
    print("💡 Falling back to default sample product catalog...")
    return [
        {
            "sku": "SKU-10948",
            "name": "Boho Chic Tufted Throw Pillow",
            "description": "A gorgeous, cream-colored woven cotton throw pillow with elegant hand-knotted tassels. Perfect for adding texture and warmth to your boho-chic living room sofa.",
            "category": "Pillows",
        },
        {
            "sku": "SKU-88492",
            "name": "Minimalist Oakwood Bedside Nightstand",
            "description": "Sleek, natural oak bedside table with one drawer and minimalist matte black metal legs. Brings a clean Scandinavian design style to your bedroom.",
            "category": "Furniture",
        },
        {
            "sku": "SKU-34092",
            "name": "Emerald Green Velvet Accent Armchair",
            "description": "Luxurious deep emerald green velvet armchair with padded armrests and elegant tapered brass gold legs. Adds mid-century modern sophistication.",
            "category": "Furniture",
        },
        {
            "sku": "SKU-57281",
            "name": "Industrial Matte Black Tripod Floor Lamp",
            "description": "Sleek matte black metal tripod floor lamp featuring a vintage amber Edison bulb. Creates warm, comfortable, ambient lighting for any modern reading nook.",
            "category": "Lighting",
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
    """Provision BigQuery dataset/tables, create GCS bucket, populate category guidelines and sample data."""
    
    # 1. Determine GCP configuration from environment or default context
    _, project_default = google.auth.default()
    project_id = os.environ.get("GCP_PROJECT_ID", project_default)
    location = os.environ.get("GCP_LOCATION", "us-central1")
    
    bq_dataset = os.environ.get("BQ_DATASET", "retail_catalog_dataset")
    bq_products_table = os.environ.get("BQ_PRODUCTS_TABLE", "products")
    bq_tags_table = os.environ.get("BQ_TAGS_TABLE", "product_tags")
    
    products_table_id = f"{project_id}.{bq_dataset}.{bq_products_table}"
    tags_table_id = f"{project_id}.{bq_dataset}.{bq_tags_table}"
    
    bucket_name = os.environ.get("GCS_BUCKET_NAME", f"retail_product_media_{project_id}")

    print("=" * 80)
    print(f"🛠️  STARTING GCP PROVISIONING SCRIPT (Generic Retail Support)")
    print(f"   GCP Project ID:  {project_id}")
    print(f"   Location/Region: {location}")
    print(f"   Target GCS Bucket: {bucket_name}")
    print(f"   Target BQ Tables:  {products_table_id}")
    print(f"                      {tags_table_id}")
    print("=" * 80)

    # Initialize clients
    bq_client = bigquery.Client(project=project_id)
    storage_client = storage.Client(project=project_id)

    # --------------------------------------------------------------------------
    # 2. Provision BigQuery Dataset & Tables
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

    # 2a. Create Products Table (Drop first to refresh schema)
    products_table_ref = bigquery.TableReference(dataset_ref, bq_products_table)
    try:
        bq_client.delete_table(products_table_ref)
        print(f"ℹ Deleted old BigQuery products table to refresh schema.")
    except NotFound:
        pass

    print(f"Creating table '{bq_products_table}' structure (category & images_gcs_folder)...")
    schema = [
        bigquery.SchemaField("sku", "STRING", mode="REQUIRED", description="Product unique SKU identifier"),
        bigquery.SchemaField("name", "STRING", mode="REQUIRED", description="Official product name"),
        bigquery.SchemaField("description", "STRING", description="Marketing details and traits description"),
        bigquery.SchemaField("category", "STRING", description="Official product category"),
        bigquery.SchemaField("images_gcs_folder", "STRING", description="GCS Folder URL holding the 360 view images of the product alone"),
    ]
    table = bigquery.Table(products_table_ref, schema=schema)
    bq_client.create_table(table)
    print(f"🎉 Successfully created BigQuery Products Table '{bq_products_table}'.")

    # 2b. Create Tags Table
    tags_table_ref = bigquery.TableReference(dataset_ref, bq_tags_table)
    try:
        bq_client.get_table(tags_table_ref)
        print(f"✓ BigQuery Table '{bq_tags_table}' already exists.")
    except NotFound:
        print(f"Table '{bq_tags_table}' not found. Creating separate tags table structure...")
        schema = [
            bigquery.SchemaField("sku", "STRING", mode="REQUIRED", description="Product unique SKU identifier"),
            bigquery.SchemaField("tags", "STRING", description="Comma-separated marketing classification tags"),
        ]
        table = bigquery.Table(tags_table_ref, schema=schema)
        bq_client.create_table(table)
        print(f"🎉 Successfully created BigQuery Tags Table '{bq_tags_table}'.")

    # --------------------------------------------------------------------------
    # 3. Provision Cloud Storage Bucket & Folder Structures
    # --------------------------------------------------------------------------
    print(f"\nProvisioning Cloud Storage bucket...")
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

    # Create keep file inside bucket
    try:
        keep_blob = bucket.blob("lifestyle_images/.keep")
        keep_blob.upload_from_string(
            "Placeholder keep file to instantiate virtual directory 'lifestyle_images/'.",
            content_type="text/plain"
        )
        print("🎉 Successfully verified 'lifestyle_images/' folder structure.")
    except Exception as folder_error:
        print(f"❌ Error creating keep file: {folder_error}")

    # 3b. Create and Upload Category Styling Guidelines
    print("\nUploading category-specific styling guidelines to GCS bucket...")
    guidelines = {
        "Pillows": """Category: Pillows
Styling & Image Guidelines:
- Always style throw pillows on a high-end, textured fabric sofa (light grey, cream, or beige) or neatly made beds.
- Ensure warm, inviting, natural sunlight streams in from the side, creating soft shadows.
- Decor should be Boho Chic, introducing hand-knotted cotton tassels, macrame elements, and green houseplants in the background.
- Maintain a clean, professional interior design magazine aesthetic. Bright and airy.""",
        
        "Furniture": """Category: Furniture
Styling & Image Guidelines:
- Furniture must be positioned in a clean, Scandinave-style minimalist room.
- Surround the product with ample breathing space to emphasize structure and clean lines.
- Incorporate natural wood finishes, matte black contrasts, and highly sophisticated home decors (like a single abstract ceramic vase or stack of linen books).
- Lighting should be soft, diffused, and comfortable. Neutral organic tones.""",
        
        "Lighting": """Category: Lighting
Styling & Image Guidelines:
- Show the tripod floor lamp styled beside a comfortable reading armchair (e.g. leather or boucle fabric) in a cozy modern nook.
- The scene should highlight the warm amber ambient glow of the Edison bulb in a dimly lit setting.
- Background details should include a rich wooden bookshelf and textured warm rugs to create contrast.
- Intimate, cozy, and premium cabin-like atmosphere."""
    }
    
    for cat, text in guidelines.items():
        blob_name = f"category_guidelines/{cat}/guidelines.txt"
        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string(text, content_type="text/plain")
            print(f"  🎉 Uploaded styling guidelines for Category '{cat}' to GCS.")
        except Exception as g_err:
            print(f"  ❌ Failed uploading guidelines for Category '{cat}': {g_err}")

    # --------------------------------------------------------------------------
    # 4. Populate BigQuery Table & Upload 360 product images to GCS
    # --------------------------------------------------------------------------
    print(f"\nPopulating products table and uploading 360-degree product images to Cloud Storage...")
    
    # Dynamically generate catalog using Gemini
    sample_products_raw = generate_mock_catalog_with_gemini()
    
    sample_products = []
    for prod in sample_products_raw:
        sku = prod["sku"]
        sample_products.append({
            "sku": sku,
            "name": prod["name"],
            "description": prod["description"],
            "category": prod["category"],
            "images_gcs_folder": f"gs://{bucket_name}/products/{sku}_360/"
        })

    # Insert products into BigQuery
    try:
        errors = bq_client.insert_rows_json(products_table_id, sample_products)
        if not errors:
            print(f"🎉 Successfully inserted {len(sample_products)} sample product rows into BigQuery products table.")
        else:
            print(f"❌ Errors inserting sample products: {errors}")
    except Exception as insert_error:
        print(f"❌ Failed to insert products data into BigQuery products table: {insert_error}")

    # Upload GCS 360 images (Front, Side, Back angles) for each product SKU
    print("Uploading simulated 360-degree visual angle images to GCS bucket...")
    angles = ["front", "side", "back"]
    color_map = {"front": "lightgrey", "side": "grey", "back": "darkgrey"}
    
    for prod in sample_products:
        sku = prod["sku"]
        name = prod["name"]
        print(f"  Uploading 360 view angles for SKU {sku} ({name})...")
        for angle in angles:
            blob_name = f"products/{sku}_360/{angle}.png"
            
            # Try to generate a real product image via Imagen, fallback to color PNG
            png_bytes = generate_mock_image_with_imagen(name, angle)
            if not png_bytes:
                print(f"    ℹ Using solid color fallback PNG for SKU {sku} ({angle} view)")
                png_bytes = create_dummy_png(color_map[angle])
                
            try:
                blob = bucket.blob(blob_name)
                blob.upload_from_string(png_bytes, content_type="image/png")
            except Exception as upload_err:
                print(f"    ❌ Failed uploading {blob_name} to GCS: {upload_err}")
                
    print("\n🏁 GCP Resources Setup Script completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    setup_resources()
