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

import asyncio
import logging
import os
from typing import Any

import nest_asyncio
import vertexai
from dotenv import load_dotenv

# A2A Starlette & ADK Core Imports
from a2a.types import AgentCapabilities, AgentCard, AgentExtension, TransportProtocol
from a2ui.adk.send_a2ui_to_client_toolset import A2uiEventConverter
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.executor.config import A2aAgentExecutorConfig
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from vertexai.preview.reasoning_engines import A2aAgent

from app.agent import app as adk_app
from app.agent import schema_manager
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()

gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")


class AgentEngineApp(A2aAgent):
    """A2A-compliant Agent Runtime Application wrapping the HR Intake ADK Agent."""

    @staticmethod
    def create(
        app: Any = None,
        artifact_service: Any = None,
        session_service: Any = None,
    ) -> Any:
        """Creates and configures an AgentEngineApp instance with A2A and A2UI support."""
        if app is None:
            app = adk_app

        def create_runner() -> Runner:
            """Creates the ADK Runner instance."""
            return Runner(
                app=app,
                session_service=session_service,
                artifact_service=artifact_service,
            )

        # Enable nesting of async event loops inside Agent Runtime/notebooks
        try:
            asyncio.get_running_loop()
            nest_asyncio.apply()
        except RuntimeError:
            pass

        agent_card = asyncio.run(AgentEngineApp.build_agent_card(app))

        # Enforce the A2UI event converter to dynamically extract `<a2ui-json>` blocks
        # and package them as structured `application/json+a2ui` A2A parts.
        a2ui_catalog = schema_manager.get_selected_catalog()
        executor_config = A2aAgentExecutorConfig(
            event_converter=A2uiEventConverter(
                catalog_key="system:a2ui_catalog", bypass_tool_check=True
            )
        )

        return AgentEngineApp(
            agent_executor_builder=lambda: A2aAgentExecutor(
                runner=create_runner(), config=executor_config
            ),
            agent_card=agent_card,
        )

    @staticmethod
    async def build_agent_card(app: Any) -> AgentCard:
        """Dynamically constructs the Agent Card capability manifest."""
        agent_card_builder = AgentCardBuilder(
            agent=app.root_agent,
            capabilities=AgentCapabilities(
                streaming=False,
                extensions=[
                    AgentExtension(
                        uri="https://a2ui.org/a2a-extension/a2ui/v0.9",
                        description="Provides agent driven UI using the A2UI JSON format v0.9.",
                    ),
                ],
            ),
            rpc_url="http://localhost:9999/",
            agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
        )
        agent_card = await agent_card_builder.build()
        agent_card.preferred_transport = TransportProtocol.http_json
        agent_card.supports_authenticated_extended_card = True
        return agent_card

    def set_up(self) -> None:
        """Initializes telemetry and Vertex AI credentials."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Registers structural session feedback to Cloud Logging."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers routing operations including standard A2A extension routes."""
        operations = super().register_operations()
        operations[""] = [*operations.get("", []), "register_feedback"]
        return operations

    def clone(self) -> "AgentEngineApp":
        return self


# Instantiate A2A runtime agent
agent_runtime = AgentEngineApp.create(
    app=adk_app,
    artifact_service=(
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    ),
    session_service=InMemorySessionService(),
)
