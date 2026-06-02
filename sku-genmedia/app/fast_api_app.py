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

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    a2a=False,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "sku-genmedia"
app.description = "API for interacting with the Agent sku-genmedia"

# Manually configure and expose A2A REST endpoints to serve Gemini Enterprise A2A calls
import json
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from a2a.server.apps.rest.rest_adapter import RESTAdapter
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from a2a.types import AgentCard
from app.agent import app as adk_app

agent_json_path = os.path.join(AGENT_DIR, "app", "agent.json")
if os.path.exists(agent_json_path):
    with open(agent_json_path, "r", encoding="utf-8") as f:
        card_data = json.load(f)
        agent_card = AgentCard(**card_data)

    def create_runner() -> Runner:
        return Runner(
            app=adk_app,
            session_service=InMemorySessionService(),
            artifact_service=InMemoryArtifactService(),
        )

    agent_executor = A2aAgentExecutor(runner=create_runner)
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    rest_adapter = RESTAdapter(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    router = APIRouter()
    for route, callback in rest_adapter.routes().items():
        router.add_api_route(
            f"/a2a/app{route[0]}", callback, methods=[route[1]]
        )

    @router.get("/a2a/app/.well-known/agent-card.json")
    async def get_agent_card(request: Request) -> Response:
        card = await rest_adapter.handle_get_agent_card(request)
        return JSONResponse(card)

    app.include_router(router)



@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
