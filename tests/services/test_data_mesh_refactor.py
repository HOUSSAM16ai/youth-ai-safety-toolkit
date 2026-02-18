import pytest


@pytest.mark.asyncio
async def test_data_mesh_refactor_verification(async_client):
    """
    Verifies that the Data Mesh endpoints have been successfully moved to their own router
    and that the legacy Intelligent Platform endpoints are updated/removed.
    """
    client = async_client

    # 1. Verify New Data Mesh Contract Endpoint (POST /api/v1/data-mesh/contracts)
    # Note: The Blueprint maps it to /api/v1/data-mesh

    contract_payload = {
        "domain": "customer",
        "name": "Customer 360",
        "description": "Unified Customer View",
        "schema_version": "1.0",
        "schema_definition": {"type": "record", "fields": []},
    }

    response = await client.post("/api/v1/data-mesh/contracts", json=contract_payload)

    # We expect authentication failure or success or validation error, but NOT 404
    assert response.status_code != 404, "Data Mesh Contract endpoint not found at new location"

    # 2. Verify New Data Mesh Metrics Endpoint (GET /api/v1/data-mesh/metrics)
    response = await client.get("/api/v1/data-mesh/metrics")
    assert response.status_code != 404, "Data Mesh Metrics endpoint not found at new location"

    # 3. Verify Observability Metrics (GET /api/observability/metrics)
    # Update: Observability has been decoupled into a separate microservice.
    # The Monolith (core-kernel) should NOT serve this anymore.
    # So we EXPECT 404 here when querying the Monolith directly.
    response = await client.get("/api/observability/metrics")
    assert response.status_code == 404, "Observability Metrics should be removed from Monolith (Decoupled)"

    # 4. Verify AIOps Telemetry (POST /api/v1/platform/aiops/telemetry)
    # Verify legacy endpoint is removed (Dead Code Cleanup)
    telemetry_payload = {"service_name": "test-service", "metric_type": "gauge", "value": 42.0}
    response = await client.post("/api/v1/platform/aiops/telemetry", json=telemetry_payload)
    assert response.status_code == 404, (
        "Legacy Telemetry endpoint should be removed (Dead Code Cleanup)"
    )

    # 5. Verify that legacy endpoints are gone
    response = await client.post("/api/v1/platform/data-mesh/contracts", json=contract_payload)
    assert response.status_code == 404, (
        "Legacy Data Mesh endpoint should be removed from Platform router"
    )
