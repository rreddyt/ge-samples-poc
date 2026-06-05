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

import pytest

from app.agent_runtime_app import AgentEngineApp


@pytest.fixture
def agent_app(monkeypatch: pytest.MonkeyPatch) -> AgentEngineApp:
    """Fixture to create and set up AgentEngineApp instance"""
    # Set integration test flag to mock external services
    monkeypatch.setenv("INTEGRATION_TEST", "TRUE")

    from app.agent_runtime_app import agent_runtime

    agent_runtime.set_up()
    return agent_runtime


@pytest.mark.asyncio
async def test_agent_stream_query_sync(agent_app: AgentEngineApp) -> None:
    """Test standard ADK stream_query method."""
    response_stream = agent_app.stream_query(
        message="What is the capital of France?",
        user_id="test-user",
    )
    events = list(response_stream)
    assert len(events) > 0


@pytest.mark.asyncio
async def test_agent_stream_query_async(agent_app: AgentEngineApp) -> None:
    """Test standard ADK async_stream_query method."""
    events = []
    async for event in agent_app.async_stream_query(
        message="What is the capital of France?",
        user_id="test-user",
    ):
        events.append(event)
    assert len(events) > 0
