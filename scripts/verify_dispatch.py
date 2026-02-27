"""
Verification Script for Mission Dispatch (Monolith -> Microservice)

This script simulates the `MissionComplexHandler` logic to verify that it successfully
dispatches a mission to the `orchestrator-service` instead of running it locally.
"""

import asyncio
import logging
import os
import sys
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_dispatch")

# Mock the dependencies to isolate the dispatch logic
# We want to verify that orchestrator_client.create_mission is called.

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

class MockAsyncClient:
    async def post(self, url, json=None, headers=None):
        logger.info(f"MOCK POST: {url} payload={json}")
        if "/missions" in url:
             return MockResponse({
                 "id": 12345,
                 "objective": json.get("objective"),
                 "status": "pending",
                 "created_at": "2023-01-01T00:00:00Z",
                 "updated_at": "2023-01-01T00:00:00Z",
                 "result": {}
             })
        return MockResponse({}, 404)

    async def get(self, url):
        logger.info(f"MOCK GET: {url}")
        return MockResponse({}, 200)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


# Patching get_http_client to return our MockAsyncClient
import app.core.http_client_factory

def mock_get_http_client(*args, **kwargs):
    return MockAsyncClient()

app.core.http_client_factory.get_http_client = mock_get_http_client

# Import User BEFORE Mission to resolve SQLModel circular relationship issues
# This is a known issue when testing SQLModel models in isolation without the full app context loading order
# We also need to import chat domain to register AdminConversation/CustomerConversation
import app.core.domain.chat # This should define AdminConversation
import app.core.domain.user
import app.core.domain.mission

# Now import the modules under test
from app.infrastructure.clients.orchestrator_client import orchestrator_client
from app.services.overmind.entrypoint import start_mission

async def verify():
    print("🚀 Starting Dispatch Verification...")

    objective = "Test Mission Dispatch"
    initiator_id = 1

    try:
        # Call the unified entrypoint
        mission = await start_mission(
            session=None, # Should be unused
            objective=objective,
            initiator_id=initiator_id,
            force_research=True
        )

        print(f"✅ Mission Created: ID={mission.id}, Status={mission.status}")

        if mission.id == 12345:
            print("✅ Verified: Mission ID matches Mock response.")
        else:
            print(f"❌ Verification Failed: ID mismatch (Expected 12345, got {mission.id})")
            sys.exit(1)

        # Check if log indicates delegation (simulated by checking if we hit the mock)
        # In a real integration test, we would check the server logs or state.

    except Exception as e:
        print(f"❌ Verification Failed with Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify())
