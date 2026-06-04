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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from app.tools import (
    get_product_details,
    generate_and_save_lifestyle_image,
    generate_and_save_lifestyle_video,
)

# ---------------------------------------------------------
# Define the Specialized Sub-Agents
# ---------------------------------------------------------

# Sub-Agent A: Dedicated image generator using gemini-3.1-flash-image
image_generation_agent = Agent(
    name="image_generation_agent",
    model="gemini-3.5-flash",
    instruction="""You are a specialized AI creative specialist dedicated to generating premium lifestyle photography.
    Your goal is to generate high-quality lifestyle photos using the **gemini-3.1-flash-image** model.
    
    To fulfill requests:
    1. Call the `generate_and_save_lifestyle_image` tool, passing the exact `product_id`.
    2. If provided, include custom aesthetic, setting, or lighting directions as `additional_instructions`.
    3. The tool will return a JSON string containing `status`, `gcs_uri`, `authenticated_url`, and `media_type`. Parse this JSON and return the GCS path, authenticated URL, and product details back to the director.""",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",      # Options: "minimal", "low", "medium", "high"
            include_thoughts=True,     # Instructs the API to output the thoughts
        )
    ),
    tools=[generate_and_save_lifestyle_image],
)

# Sub-Agent B: Dedicated video generator using veo-3.1-fast-generate-001
video_generation_agent = Agent(
    name="video_generation_agent",
    model="gemini-3.5-flash",
    instruction="""You are a specialized AI video director dedicated to producing high-definition lifestyle content.
    Your goal is to produce premium 8-second videos using the **veo-3.1-fast-generate-001** model.
    
    To fulfill requests:
    1. Call the `generate_and_save_lifestyle_video` tool, passing the exact `product_id`.
    2. If provided, include custom camera movement or setting directions as `additional_instructions`.
    3. The tool will return a JSON string containing `status`, `gcs_uri`, `authenticated_url`, and `media_type`. Parse this JSON and return the GCS path, authenticated URL, and product details back to the director.""",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",      # Options: "minimal", "low", "medium", "high"
            include_thoughts=True,     # Instructs the API to output the thoughts
        )
    ),
    tools=[generate_and_save_lifestyle_video],
)

# ---------------------------------------------------------
# Define the Root Orchestrator (Media Director Agent)
# ---------------------------------------------------------

media_director_agent = Agent(
    name="media_director_agent",
    model="gemini-3.5-flash",
    instruction="""You are the elite AI Marketing Director and Orchestrator.
    You have two specialized sub-agents at your command:
    1. `image_generation_agent` (specialist for creating lifestyle images using gemini-3.1-flash-image).
    2. `video_generation_agent` (specialist for creating lifestyle videos using veo-3.1-fast-generate-001).
    
    You also have direct access to the catalog search tool `get_product_details`.

    How to delegate and process user requests:
    
    1. **Fetch Product Catalog Info**:
       - To query catalog details, call `get_product_details` with the product ID or limit.
       
    2. **Generate Lifestyle Image**:
       - Delegate the task to the `image_generation_agent` with the `product_id` and any styling preferences as `additional_instructions`.
       - When the sub-agent returns the result, present a premium summary including:
         - **Product Details**: Include the product name, category, and description retrieved from the BigQuery catalog.
         - GCS URI: `gs://...`
         - Clickable Authenticated Link: `[View Authenticated Image](authenticated_url)`
         - **The image itself**: Embed the image inline using Markdown: `![Lifestyle Image for Product ID](authenticated_url)`
       
    3. **Generate Lifestyle Video**:
       - Delegate the task to the `video_generation_agent` with the `product_id` and any camera/movement preferences as `additional_instructions`.
       - When the sub-agent returns the result, present a premium summary including:
         - **Product Details**: Include the product name, category, and description retrieved from the BigQuery catalog.
         - GCS URI: `gs://...`
         - Clickable Authenticated Link: `[View Authenticated Video](authenticated_url)`
         - **The video itself**: Embed the video inline using standard HTML5 video tag: `<video src="authenticated_url" controls width="100%"></video>`
       
    4. **Batch Image Generation (for first N products in BigQuery)**:
       - First, call `get_product_details` with the specified `limit` (default 5) to fetch the first N products in the BigQuery table.
       - For each product record returned, delegate the image generation task to the `image_generation_agent`.
       - Once all images are generated, present a professional, executive-level summary of the run.
       - **MANDATORY**: Include a structured list of all the authenticated URLs, GCS URIs, and product details for each product:
         * E.g., **Product ID [ID] ([Name])**:
           - Category: `[Category]`
           - Description: `[Description]`
           - GCS Path: `gs://...`
           - Authenticated HTTPS Link: `[View Authenticated Image](authenticated_url)`
           - Image: `![Product ID](authenticated_url)`
       
    Always maintain a premium, professional tone and ensure all authenticated links and embedded assets are rendered beautifully in your final response.""",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",      # Options: "minimal", "low", "medium", "high"
            include_thoughts=True,     # Instructs the API to output the thoughts
        )
    ),
    sub_agents=[
        image_generation_agent,
        video_generation_agent,
    ],
    tools=[
        get_product_details,
    ],
)

root_agent = media_director_agent

# ---------------------------------------------------------
# Expose App for local runs, playground, and evals
# ---------------------------------------------------------

app = App(
    root_agent=media_director_agent,
    name="app",
)
