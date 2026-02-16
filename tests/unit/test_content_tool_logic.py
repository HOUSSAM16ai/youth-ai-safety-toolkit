"""Unit tests for content tool logic - aligned with ResearchClient decoupling."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock external modules BEFORE importing app modules
sys.modules["dspy"] = MagicMock()
sys.modules["llama_index"] = MagicMock()
sys.modules["llama_index.core"] = MagicMock()
sys.modules["llama_index.core.schema"] = MagicMock()
sys.modules["llama_index.core.vector_stores"] = MagicMock()
sys.modules["llama_index.embeddings.huggingface"] = MagicMock()
sys.modules["llama_index.vector_stores.supabase"] = MagicMock()

import pytest

# Import the module under test
from app.services.chat.tools import content as content_module


@pytest.fixture(autouse=True)
def mock_research_client():
    """Mock the research_client instance in the content module."""
    with patch("app.services.chat.tools.content.research_client", autospec=True) as mock_client:
        # Setup AsyncMocks for async methods
        mock_client.deep_research = AsyncMock()
        mock_client.get_curriculum_structure = AsyncMock()
        mock_client.get_content_raw = AsyncMock()
        yield mock_client


@pytest.mark.asyncio
async def test_search_content_uses_research_client(mock_research_client):
    """Verify that search_content uses ResearchClient."""
    # Setup mock result
    mock_research_client.deep_research.return_value = "Detailed Report Content"

    results = await content_module.search_content(q="Test Query")

    assert len(results) == 1
    assert results[0]["id"] == "research_report"
    assert results[0]["content"] == "Detailed Report Content"
    mock_research_client.deep_research.assert_called_once()


@pytest.mark.asyncio
async def test_search_content_error_handling(mock_research_client):
    """Verify search_content propagates client failures (Fail-Fast)."""
    # Updated expectation: The code propagates exceptions to the TaskExecutor
    mock_research_client.deep_research.side_effect = Exception("Network error")

    with pytest.raises(Exception, match="Network error"):
        await content_module.search_content(q="Error Query")


@pytest.mark.asyncio
async def test_search_content_soft_failure(mock_research_client):
    """Verify search_content detects JSON error strings (Soft Failures)."""
    # Simulate a "soft failure" where the tool returns an error as a JSON string
    mock_research_client.deep_research.return_value = '{"type": "error", "content": "Soft failure occurred"}'

    # Expect ValueError due to strict validation
    with pytest.raises(ValueError, match="Research Tool Error: Soft failure occurred"):
        await content_module.search_content(q="Soft Fail Query")


@pytest.mark.asyncio
async def test_get_curriculum_structure(mock_research_client):
    """Test curriculum structure retrieval."""
    mock_research_client.get_curriculum_structure.return_value = {"3as": {"subjects": []}}

    result = await content_module.get_curriculum_structure(level="3as")

    assert "3as" in result
    mock_research_client.get_curriculum_structure.assert_called_with("3as")


@pytest.mark.asyncio
async def test_get_content_raw(mock_research_client):
    """Test raw content retrieval."""
    mock_research_client.get_content_raw.return_value = {
        "content": "# Exercise",
        "solution": "# Solution",
    }

    result = await content_module.get_content_raw("ex-123", include_solution=True)

    assert result is not None
    assert "content" in result
    mock_research_client.get_content_raw.assert_called_with("ex-123", include_solution=True)


@pytest.mark.asyncio
async def test_get_solution_raw(mock_research_client):
    """Test solution retrieval."""
    mock_research_client.get_content_raw.return_value = {
        "content": "# Exercise",
        "solution": "# Official Solution",
    }

    result = await content_module.get_solution_raw("ex-123")

    assert result is not None
    assert result["solution_md"] == "# Official Solution"
    # Note: get_solution_raw calls get_content_raw with include_solution=True
    mock_research_client.get_content_raw.assert_called_with("ex-123", include_solution=True)


@pytest.mark.asyncio
async def test_normalize_branch():
    """Test branch normalization logic."""
    # Test matching variant
    result = content_module._normalize_branch("علوم تجريبية")
    # Should return a normalized label
    assert result is not None

    # Test None input
    assert content_module._normalize_branch(None) is None

    # Test empty string
    assert content_module._normalize_branch("") is None
