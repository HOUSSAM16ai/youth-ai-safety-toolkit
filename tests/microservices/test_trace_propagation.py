from fastapi.testclient import TestClient

from microservices.api_gateway.main import app

client = TestClient(app)

def test_trace_propagation_existing_header():
    """
    Verify that if a 'traceparent' header is provided in the request,
    it is passed through to the response (and implicitly to downstream services).
    """
    trace_id = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    headers = {"traceparent": trace_id}

    response = client.get("/health", headers=headers)

    assert response.status_code == 200
    assert "traceparent" in response.headers
    assert response.headers["traceparent"] == trace_id

def test_trace_propagation_generates_header():
    """
    Verify that if no 'traceparent' header is provided,
    a new one is generated and attached to the response.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert "traceparent" in response.headers
    assert response.headers["traceparent"].startswith("00-")
    assert len(response.headers["traceparent"].split("-")) == 4
