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

import asyncio
from google.cloud import bigquery
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Local imports from the consolidated project structure
from app.agent import catalog_enrichment_workflow, bq_client

# Ensure standard environment vars are configured for local Vertex AI access
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

async def process_catalog(limit: int = 5):
    """Executes the ADK sequential multi-agent workflow for BigQuery products at scale.

    Args:
        limit: Number of products to process (default is 5 for safety/demo, scalable up to 40000).
    """
    from app.agent import products_table_id, tags_table_id, bucket_name

    print("=" * 80)
    print(f"🚀 STARTING GENERIC RETAIL SKU MARKETING DEMO (Consolidated Project Folder)")
    print(f"   Source BigQuery Table (Products): {products_table_id}")
    print(f"   Target BigQuery Table (Tags):     {tags_table_id}")
    print(f"   Target Storage Bucket (Images):   {bucket_name}")
    print(f"   Target limit of products to process: {limit}")
    print("=" * 80)

    # Initialize standard ADK services
    session_service = InMemorySessionService()
    runner = Runner(
        agent=catalog_enrichment_workflow, 
        app_name="app", 
        session_service=session_service
    )

    try:
        # Fetch products from BigQuery securely
        print(f"\nFetching up to {limit} products from BigQuery...")
        query = f"SELECT sku, name, description, category, images_gcs_folder FROM `{products_table_id}` LIMIT @limit"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
        )
        products = bq_client.query(query, job_config=job_config).result()
    except Exception as e:
        print(f"\n❌ Failed to query BigQuery table '{products_table_id}'. Ensure your GCP credentials are set and the dataset exists.")
        print(f"Error details: {e}")
        print("\n💡 For the demo to proceed, let's simulate BigQuery products locally!")
        
        # Simulated products for local demo fallback
        class SimulatedRow:
            def __init__(self, sku, name, description, category, images_gcs_folder):
                self.sku = sku
                self.name = name
                self.description = description
                self.category = category
                self.images_gcs_folder = images_gcs_folder
        
        products = [
            SimulatedRow(
                sku="SKU-10948",
                name="Boho Chic Tufted Throw Pillow",
                description="A gorgeous, cream-colored woven cotton throw pillow with elegant hand-knotted tassels. Perfect for adding texture and warmth to your boho-chic living room sofa.",
                category="Pillows",
                images_gcs_folder=f"gs://{bucket_name}/products/SKU-10948_360/"
            ),
            SimulatedRow(
                sku="SKU-88492",
                name="Minimalist Oakwood Bedside Nightstand",
                description="Sleek, natural oak bedside table with one drawer and minimalist matte black metal legs. Brings a clean Scandinavian design style to your bedroom.",
                category="Furniture",
                images_gcs_folder=f"gs://{bucket_name}/products/SKU-88492_360/"
            )
        ]
        print("Loaded 2 simulated products for the local run.")

    print("\n" + "-" * 50)
    for idx, row in enumerate(products, 1):
        print(f"\n[{idx}] Processing Product SKU: {row.sku}...")
        print(f"    Name: {row.name}")
        print(f"    Category: {row.category}")
        print(f"    360 Folder: {row.images_gcs_folder}")
        
        # Create a unique ADK session for each product SKU
        session_id = f"session-{row.sku}"
        session = await session_service.create_session(
            app_name="app", 
            user_id="marketing_system",
            session_id=session_id
        )
        
        # Assemble the user request for the multi-agent workflow
        parts = []
        user_prompt = f"""
        Please execute the enrichment workflow for the product catalog.
        Product Details:
        SKU: {row.sku}
        Name: {row.name}
        Description: {row.description}
        Category: {row.category}
        GCS folder of 360 images: {row.images_gcs_folder}
        
        Analyze the attached 360-degree images of the product alone to understand its visual appearance from all angles.
        """
        parts.append(types.Part.from_text(text=user_prompt))

        # Dynamically list and retrieve GCS 360 images to append as multimodal visuals
        try:
            # Parse bucket and prefix from gs://bucket/prefix
            gcs_path = row.images_gcs_folder.replace("gs://", "")
            path_parts = gcs_path.split("/", 1)
            src_bucket_name = path_parts[0]
            src_prefix = path_parts[1] if len(path_parts) > 1 else ""
            
            from google.cloud import storage
            sc = storage.Client()
            bucket = sc.bucket(src_bucket_name)
            blobs = list(bucket.list_blobs(prefix=src_prefix))
            
            for blob in blobs:
                if blob.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_uri = f"gs://{src_bucket_name}/{blob.name}"
                    print(f"      📎 Attaching Multimodal Image Part: {img_uri}")
                    parts.append(types.Part.from_uri(file_uri=img_uri, mime_type="image/png"))
        except Exception as gcs_err:
            print(f"      ⚠️ Warning: Could not retrieve 360 GCS images: {gcs_err}")

        user_message = types.Content(role="user", parts=parts)
        
        # Run the Sequential Agent Workflow and print events
        print(f"    Running Collaborative Workflow (Tagging Agent -> Creative Image Agent)...")
        try:
            async for event in runner.run_async(
                user_id="marketing_system",
                session_id=session.id,
                new_message=user_message
            ):
                # Print real-time tool executions or final outputs as they arrive
                if event.content and event.content.parts:
                    text_part = event.content.parts[0].text
                    if text_part:
                        # Trim output for readability
                        preview = text_part.strip().split("\n")[0]
                        print(f"      ↳ [Event from {event.author}]: {preview}...")
                        
                # Check if this is the final response
                if event.is_final_response() and event.content:
                    print(f"\n    ✅ Enrichment Workflow Completed for SKU {row.sku}!")
                    print(f"    Summary Output:\n{event.content.parts[0].text}")
        except Exception as run_error:
            print(f"    ❌ Error running workflow for SKU {row.sku}: {run_error}")
            
        print("\n" + "-" * 50)

    print("\n🏁 SKU Marketing Demo finished execution.")
    print("=" * 80)

if __name__ == "__main__":
    # Set demo limits (5 products for initial testing, scalable to 40000)
    asyncio.run(process_catalog(limit=2))
