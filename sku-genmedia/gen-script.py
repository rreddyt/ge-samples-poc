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
import asyncio

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Disable client certificate checks to avoid mTLS helper segfault issues in this environment
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

from google.cloud import bigquery
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Local imports from the new project structure
from app.agent import media_director_agent
from app.tools import project_id, bq_dataset, bq_table, bq_client, gcs_bucket

# Ensure standard environment vars are configured for Vertex AI access
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GEMINI_LOCATION", os.environ.get("GCP_LOCATION", "global"))
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

async def process_catalog(limit: int = 5):
    """Executes the ADK media generation agent for BigQuery products at scale."""
    products_table_id = f"{project_id}.{bq_dataset}.{bq_table}"

    print("=" * 80)
    print(f"🚀 STARTING RETAIL SKU MARKETING DEMO (ADK Media Generation Agent)")
    print(f"   Source BigQuery Table:          {products_table_id}")
    print(f"   Target Storage Bucket (Media):  {gcs_bucket}")
    print(f"   Target limit of products:       {limit}")
    print("=" * 80)

    # Initialize standard ADK services
    session_service = InMemorySessionService()
    runner = Runner(
        agent=media_director_agent, 
        app_name="app", 
        session_service=session_service
    )

    try:
        # Fetch products from BigQuery securely
        print(f"\nFetching up to {limit} products from BigQuery...")
        query = f"SELECT `product-id`, `product-name` FROM `{products_table_id}` LIMIT @limit"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
        )
        products = bq_client.query(query, job_config=job_config).result()
    except Exception as e:
        print(f"\n❌ Failed to query BigQuery table '{products_table_id}'. Ensure your GCP credentials are set and the dataset exists.")
        print(f"Error details: {e}")
        return

    print("\n" + "-" * 50)
    for idx, row in enumerate(products, 1):
        product_id = row["product-id"]
        product_name = row["product-name"]
        
        print(f"\n[{idx}] Processing Product ID: {product_id}...")
        print(f"    Name: {product_name}")
        
        # Create a unique ADK session for each product
        session_id = f"session-{product_id}"
        session = await session_service.create_session(
            app_name="app", 
            user_id="marketing_system",
            session_id=session_id
        )
        
        user_prompt = f"Please generate a lifestyle image for product ID {product_id}."
        user_message = types.Content(
            role="user", 
            parts=[types.Part.from_text(text=user_prompt)]
        )
        
        print(f"    Running ADK Agent runner to generate lifestyle image...")
        try:
            async for event in runner.run_async(
                user_id="marketing_system",
                session_id=session.id,
                new_message=user_message
            ):
                # Check if this is the final response
                if event.is_final_response() and event.content:
                    print(f"\n    ✅ Content Generation Completed for Product {product_id}!")
                    print(f"    Summary Output:\n{event.content.parts[0].text}")
        except Exception as run_error:
            print(f"    ❌ Error running agent for Product {product_id}: {run_error}")
            
        print("\n" + "-" * 50)

    print("\n🏁 SKU Marketing Demo finished execution.")
    print("=" * 80)

if __name__ == "__main__":
    # Set demo limit
    asyncio.run(process_catalog(limit=2))
