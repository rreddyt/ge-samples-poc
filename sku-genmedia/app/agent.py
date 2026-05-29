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
from google.adk.agents import Agent, SequentialAgent
from google.adk.apps import App
from google.adk.models import Gemini

# Import all GCP clients, configs, and tools from tools.py
from app.tools import (
    update_bq_tags,
    generate_lifestyle_image,
    list_product_360_images,
    read_category_guidelines,
    bq_client,
    storage_client,
    project_id,
    bq_dataset,
    bq_products_table,
    bq_tags_table,
    products_table_id,
    tags_table_id,
    bucket_name,
)

# ---------------------------------------------------------
# Define the Collaborative Agents
# ---------------------------------------------------------

# Agent A: Handles categorisation and catalog enrichment tags
tagging_agent = Agent(
    name="tagging_agent",
    model="gemini-2.5-flash",
    instruction="""You are a premium retail catalog analyst for a high-end retail brand.
    Given a product's SKU, Name, and Description:
    1. Analyze the product traits and design style.
    2. Formulate a list of 5-10 highly relevant, descriptive tags suitable for search filtering and categorization.
    3. Call the `update_bq_tags` tool to save these tags to the BigQuery database.
    4. Provide a concise summary of the generated tags in your output.""",
    tools=[update_bq_tags],
)

# Agent B: Handles composing high-end marketing prompts and calling image generation using GCS 360 views and GCS category styling guidelines
image_agent = Agent(
    name="image_agent",
    model="gemini-2.5-flash",
    instruction="""You are an elite creative director for a high-end retail brand.
    Given a product's SKU, Name, Description, Category, and GCS folder of 360 product images:
    1. Call the `read_category_guidelines` tool with the product Category to fetch the specific brand styling and image guidelines for this category.
    2. Call the `list_product_360_images` tool with the SKU to locate all GCS images showing the product alone from all angles.
    3. Review the product's visual appearance from all visual angles (front, side, back, shape, texture, color, styling details) provided inside the GCS images.
    4. Compose a highly detailed, premium prompt for Google's Imagen 3 model to render this product styled inside an aspirational consumer lifestyle setting.
       - You MUST strictly follow the styling, lights, background, and room rules fetched from your `read_category_guidelines` tool call.
       - Focus on positioning the product exactly as it looks in the images (e.g. details from the 360 angles), styled beautifully according to the category guidelines.
       - Avoid plain or chaotic backdrops; use beautiful, harmonious living spaces.
    5. Call the `generate_lifestyle_image` tool with the SKU, product name, a representative product GCS image path (e.g., front.png), and your composed creative prompt to render and store the lifestyle image in GCS.
    6. Return the GCS URL of the successfully generated lifestyle image.""",
    tools=[generate_lifestyle_image, list_product_360_images, read_category_guidelines],
)


# ---------------------------------------------------------
# Define the Multi-Agent Sequential Workflow & App
# ---------------------------------------------------------

# SequentialAgent executes agents in order: Tagging -> Creative Image Gen
catalog_enrichment_workflow = SequentialAgent(
    name="catalog_enrichment_workflow",
    sub_agents=[tagging_agent, image_agent],
)

root_agent = catalog_enrichment_workflow

# Expose App for agents-cli local playground, run, and evaluation
app = App(
    root_agent=catalog_enrichment_workflow,
    name="app",
)


