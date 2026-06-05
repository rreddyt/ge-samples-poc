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
import os

from app.tools import (
    get_product_details,
    generate_and_save_lifestyle_image,
    generate_and_save_lifestyle_video,
    approve_media_review,
    update_regenerated_media_status,
)

# ---------------------------------------------------------
# Define after_model_callback to append raw media bytes
# ---------------------------------------------------------

def attach_media_bytes_to_response(
    callback_context, llm_response
) -> None:
    """Scan the model response for public GCS media URLs and append them as inline_data parts.
    
    This allows the chat UI (Gemini Enterprise) to natively render the generated images/videos.
    """
    if not llm_response.content or not llm_response.content.parts:
        return

    import re
    from app.tools import get_storage_client

    # Regex to match markdown image tags containing GCS public URLs
    markdown_image_pattern = re.compile(
        r"!\[[^\]]*\]\((https://storage\.googleapis\.com/([^/\s]+)/([^\s\)\"\'>\n]+))\)"
    )
    
    # Regex to capture GCS public URLs (general search)
    gcs_url_pattern = re.compile(
        r"https://storage\.googleapis\.com/([^/\s]+)/([^\s\)\"\'>\n]+)"
    )

    new_parts = list(llm_response.content.parts)
    detected_blobs = set()

    for part in llm_response.content.parts:
        if not part.text:
            continue
        
        # 1. Process markdown image tags first
        md_matches = markdown_image_pattern.findall(part.text)
        for full_url, bucket_name, blob_name in md_matches:
            blob_key = f"gs://{bucket_name}/{blob_name}"
            
            # Remove the markdown image tag from the response text
            part.text = re.sub(rf"!\[[^\]]*\]\({re.escape(full_url)}\)", "", part.text)
            
            if blob_key in detected_blobs:
                continue
            detected_blobs.add(blob_key)
            
            # Determine mime type from extension
            ext = blob_name.lower().split(".")[-1]
            mime_type = None
            if ext in ("jpg", "jpeg"):
                mime_type = "image/jpeg"
            elif ext == "png":
                mime_type = "image/png"
            
            if mime_type:
                try:
                    bucket = get_storage_client().bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    data = blob.download_as_bytes()
                    inline_blob = types.Blob(mime_type=mime_type, data=data)
                    new_parts.append(types.Part(inline_data=inline_blob))
                    print(f"[after_model_callback] Appended inline media {blob_key} ({mime_type}) from markdown tag.")
                except Exception as e:
                    print(f"[after_model_callback] Failed to download {blob_key}: {e}")

        # 2. Process any remaining plain GCS URLs
        matches = gcs_url_pattern.findall(part.text)
        for bucket_name, blob_name in matches:
            blob_key = f"gs://{bucket_name}/{blob_name}"
            if blob_key in detected_blobs:
                continue
            detected_blobs.add(blob_key)
            
            # Determine mime type from extension
            ext = blob_name.lower().split(".")[-1]
            mime_type = None
            if ext in ("jpg", "jpeg"):
                mime_type = "image/jpeg"
            elif ext == "png":
                mime_type = "image/png"
            
            if mime_type:
                try:
                    bucket = get_storage_client().bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    data = blob.download_as_bytes()
                    inline_blob = types.Blob(mime_type=mime_type, data=data)
                    new_parts.append(types.Part(inline_data=inline_blob))
                    print(f"[after_model_callback] Appended inline media {blob_key} ({mime_type}) from plain URL.")
                except Exception as e:
                    print(f"[after_model_callback] Failed to download {blob_key}: {e}")

    llm_response.content.parts = new_parts


# ---------------------------------------------------------
# Define the Specialized Sub-Agents
# ---------------------------------------------------------

# Sub-Agent A: Dedicated image generator using gemini-3.1-flash-image
image_generation_agent = Agent(
    name="image_generation_agent",
    model="gemini-2.5-flash",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_budget=1024,
        )
    ),
    instruction="""You are a specialized AI creative specialist dedicated to generating premium lifestyle photography.
    Your goal is to generate high-quality lifestyle photos using the **gemini-3.1-flash-image** model.
    
    To fulfill requests:
    1. Call the `generate_and_save_lifestyle_image` tool, passing the exact `product_id`.
    2. If provided, include custom aesthetic, setting, or lighting directions as `additional_instructions`.
    3. If this is a regeneration of a previously generated media, pass the rejected media file name as `old_lifestyle_media_file_name`.
    4. MANDATORY: Immediately after the tool execution completes, you MUST call the `transfer_to_agent` tool to transfer control back to `root_agent`. Do not output any text response, URLs, or messages yourself; the root orchestrator will handle presenting the results to the user.""",
    tools=[generate_and_save_lifestyle_image],
)

# Sub-Agent B: Dedicated video generator using veo-3.1-fast-generate-001
video_generation_agent = Agent(
    name="video_generation_agent",
    model="gemini-2.5-flash",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_budget=1024,
        )
    ),
    instruction="""You are a specialized AI video director dedicated to producing high-definition lifestyle content.
    Your goal is to produce premium 8-second videos using the **veo-3.1-fast-generate-001** model.
    
    To fulfill requests:
    1. Call the `generate_and_save_lifestyle_video` tool, passing the exact `product_id`.
    2. If provided, include custom camera movement or setting directions as `additional_instructions`.
    3. If this is a regeneration of a previously generated media, pass the rejected media file name as `old_lifestyle_media_file_name`.
    4. MANDATORY: Immediately after the tool execution completes, you MUST call the `transfer_to_agent` tool to transfer control back to `root_agent`. Do not output any text response, URLs, or messages yourself; the root orchestrator will handle presenting the results to the user.""",
    tools=[generate_and_save_lifestyle_video],
)

# Sub-Agent C: Dedicated Image/Video Review Specialist
review_sub_agent = Agent(
    name="review_sub_agent",
    model="gemini-2.5-pro",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2048,
        )
    ),
    instruction="""You are a professional Creative Review Specialist.
    Your goal is to present generated images or videos to the user for approval or regeneration.

    When you are invoked:
    1. Show the user the generated image/video GCS path, authenticated URL, public URL, and product details.
    2. Natively render/embed the generated media directly in your response so the user can view it:
       - For images, embed it using raw markdown (MANDATORY: do not wrap in backticks or code blocks): ![Lifestyle Image](public_url)
       - For videos, embed it using a raw HTML5 video tag (MANDATORY: do not wrap in backticks or code blocks): <video src="public_url" controls width="100%"></video>
    3. Ask the user in plain text: "Would you like to approve this generated media or regenerate it?"
    
    Handle user responses:
    - **If the user says they approve** (e.g. types "Approve" or says "I approve"):
      - Call the `approve_media_review` tool, passing the correct `product_id` and `lifestyle_media_file_name`.
      - Confirm the approval with a success message in plain text.
    - **If the user says they want to regenerate** (e.g. types "Regenerate" or says "Please regenerate"):
      - Ask the user for any specific additional stylistic or camera directions (if not already provided).
      - Transfer control to `image_generation_agent` (for image files) or `video_generation_agent` (for video files) to generate the new media for that product, passing the `product_id`, `additional_instructions` (if any), and the rejected media file name as `old_lifestyle_media_file_name`.
      - Once control returns to you after regeneration, show the newly generated media (including GCS path, authenticated URL, public URL, and the actual raw embedded image ![Lifestyle Image](public_url) or video <video src="public_url" controls width="100%"></video> (do not wrap either in backticks or code blocks)) to the user and ask if they want to review it.""",
    sub_agents=[],
    tools=[
        approve_media_review,
        update_regenerated_media_status,
    ],
    after_model_callback=attach_media_bytes_to_response,
)

# ---------------------------------------------------------
# Define the Root Orchestrator (Media Director Agent)
# ---------------------------------------------------------

ROLE_DESCRIPTION = """You are the elite AI Marketing Director and Orchestrator (named `root_agent`).
You have three specialized sub-agents at your command:
1. `image_generation_agent` (specialist for creating lifestyle images using gemini-3.1-flash-image).
2. `video_generation_agent` (specialist for creating lifestyle videos using veo-3.1-fast-generate-001).
3. `review_sub_agent` (specialist for showing and processing image / video approvals and reviews).

You also have direct access to the catalog search tool `get_product_details`."""

WORKFLOW_DESCRIPTION = """Your workflow must follow these stages:

1. **Orchestrate Generation**:
   - If the user asks to generate a lifestyle image or video for a product ID, or batch generate for the first N products:
     - Call `get_product_details` if needed to resolve the product info.
     - Delegate the generation task to `image_generation_agent` or `video_generation_agent`.
     
2. **Offer Review Option**:
   - Immediately after any individual or batch generation completes:
     - Present the summary list of the generated media, including the public URL, authenticated URL, GCS path, and product ID.
     - Natively render/embed the generated media directly in your response so the user can view it:
       - For images, embed it using raw markdown (MANDATORY: do not wrap in backticks or code blocks): ![Lifestyle Image](public_url)
       - For videos, embed it using a raw HTML5 video tag (MANDATORY: do not wrap in backticks or code blocks): <video src="public_url" controls width="100%"></video>
     - Ask the user in plain text: "Would you like to review the generated media?"
     - If the user wants to review (says "yes", or replies "Review" or "StartReview"):
       - Transfer control to the `review_sub_agent` using the `transfer_to_agent` tool to begin the review loop for the generated product(s).
     - If the user chooses to skip (says "no" or "Skip" or "SkipReview"), conclude the session professionally."""

SYSTEM_INSTRUCTION = f"{ROLE_DESCRIPTION}\n\n{WORKFLOW_DESCRIPTION}"

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-pro",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2048,
        )
    ),
    instruction=SYSTEM_INSTRUCTION,
    sub_agents=[
        image_generation_agent,
        video_generation_agent,
        review_sub_agent,
    ],
    tools=[
        get_product_details,
    ],
    after_model_callback=attach_media_bytes_to_response,
)

# ---------------------------------------------------------
# Expose App for local runs, playground, and evals
# ---------------------------------------------------------

app = App(
    root_agent=root_agent,
    name="app",
)
