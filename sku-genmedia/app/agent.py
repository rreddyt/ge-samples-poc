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
    3. Return the resulting GCS path and details back to the director.""",
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
    3. Return the resulting GCS path and details back to the director.""",
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
       
    3. **Generate Lifestyle Video**:
       - Delegate the task to the `video_generation_agent` with the `product_id` and any camera/movement preferences as `additional_instructions`.
       
    4. **Batch Image Generation**:
       - First, call `get_product_details` with the specified `limit` (default 5).
       - For each product record returned, delegate the image generation task to the `image_generation_agent`.
       
    Always present a premium, professional, executive-level summary of all the generated content along with their Cloud Storage GCS URIs (gs://...).""",
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
