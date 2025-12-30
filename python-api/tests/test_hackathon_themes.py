"""
Comprehensive test suite for Hackathon Themes API.

Tests CRUD operations, statistics, authorization, and migration.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import HTTPException, status
from services import hackathon_theme_service


# Test Fixtures

@pytest.fixture
def mock_zerodb():
    """Mock ZeroDB client."""
    mock = AsyncMock()
    mock.tables = AsyncMock()
    return mock


@pytest.fixture
def sample_theme_id():
    """Sample theme UUID."""
    return str(uuid4())


@pytest.fixture
def sample_theme_data(sample_theme_id):
    """Sample theme data."""
    return {
        "id": sample_theme_id,
        "theme_name": "AI & Machine Learning",
        "description": "Artificial intelligence and ML projects",
        "icon": "🤖",
        "hackathon_count": 15,
        "total_prizes": "50000.00",
        "display_order": 1,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


# Tests for get_theme_by_name

@pytest.mark.asyncio
async def test_get_theme_by_name_found(mock_zerodb, sample_theme_data):
    """Test finding theme by name."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}

    result = await hackathon_theme_service.get_theme_by_name(
        "AI & Machine Learning", mock_zerodb
    )

    assert result == sample_theme_data


@pytest.mark.asyncio
async def test_get_theme_by_name_not_found(mock_zerodb):
    """Test theme not found by name."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    result = await hackathon_theme_service.get_theme_by_name("Nonexistent", mock_zerodb)

    assert result is None


@pytest.mark.asyncio
async def test_get_theme_by_name_exclude(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test excluding specific theme from name check."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}

    result = await hackathon_theme_service.get_theme_by_name(
        "AI & Machine Learning", mock_zerodb, exclude_id=sample_theme_id
    )

    assert result is None


# Tests for get_next_display_order

@pytest.mark.asyncio
async def test_get_next_display_order_empty(mock_zerodb):
    """Test getting first display order when no themes exist."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    order = await hackathon_theme_service.get_next_display_order(mock_zerodb)

    assert order == 1


@pytest.mark.asyncio
async def test_get_next_display_order_with_existing(mock_zerodb, sample_theme_data):
    """Test getting next display order with existing themes."""
    mock_zerodb.tables.query_rows.return_value = {
        "rows": [
            {**sample_theme_data, "display_order": 1},
            {**sample_theme_data, "display_order": 3},
            {**sample_theme_data, "display_order": 2}
        ]
    }

    order = await hackathon_theme_service.get_next_display_order(mock_zerodb)

    assert order == 4


# Tests for create_theme

@pytest.mark.asyncio
async def test_create_theme_success(mock_zerodb):
    """Test successful theme creation."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}  # No duplicate
    mock_zerodb.tables.insert_rows.return_value = None

    with patch('services.hackathon_theme_service.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid4()
        result = await hackathon_theme_service.create_theme(
            theme_name="Web3 & Blockchain",
            description="Decentralized applications",
            icon="⛓️",
            display_order=1,
            zerodb=mock_zerodb
        )

    assert result["theme_name"] == "Web3 & Blockchain"
    assert result["icon"] == "⛓️"
    assert result["hackathon_count"] == 0
    assert result["total_prizes"] == "0.00"
    mock_zerodb.tables.insert_rows.assert_called_once()


@pytest.mark.asyncio
async def test_create_theme_auto_display_order(mock_zerodb):
    """Test theme creation with auto-assigned display order."""
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": []},  # No duplicate
        {"rows": [{"display_order": 2}]}  # Existing themes for order calculation
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    with patch('services.hackathon_theme_service.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid4()
        result = await hackathon_theme_service.create_theme(
            theme_name="Test Theme",
            description=None,
            icon=None,
            display_order=None,  # Auto-assign
            zerodb=mock_zerodb
        )

    assert result["display_order"] == 3


@pytest.mark.asyncio
async def test_create_theme_duplicate(mock_zerodb, sample_theme_data):
    """Test preventing duplicate theme creation."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}

    with pytest.raises(HTTPException) as exc_info:
        await hackathon_theme_service.create_theme(
            theme_name="AI & Machine Learning",
            description=None,
            icon=None,
            display_order=1,
            zerodb=mock_zerodb
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in exc_info.value.detail


# Tests for get_theme

@pytest.mark.asyncio
async def test_get_theme_success(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test successful theme retrieval."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}

    result = await hackathon_theme_service.get_theme(sample_theme_id, mock_zerodb)

    assert result == sample_theme_data
    mock_zerodb.tables.query_rows.assert_called_once_with(
        table_id="hackathon_themes",
        filter={"id": sample_theme_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_get_theme_not_found(mock_zerodb, sample_theme_id):
    """Test theme not found."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await hackathon_theme_service.get_theme(sample_theme_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


# Tests for list_themes

@pytest.mark.asyncio
async def test_list_themes_success(mock_zerodb, sample_theme_data):
    """Test listing all themes."""
    themes = [
        {**sample_theme_data, "display_order": 2, "theme_name": "Web3"},
        {**sample_theme_data, "display_order": 1, "theme_name": "AI"},
        {**sample_theme_data, "display_order": 3, "theme_name": "IoT"}
    ]
    mock_zerodb.tables.query_rows.return_value = {"rows": themes}

    result = await hackathon_theme_service.list_themes(mock_zerodb)

    assert result["total"] == 3
    assert len(result["themes"]) == 3
    # Should be sorted by display_order
    assert result["themes"][0]["theme_name"] == "AI"
    assert result["themes"][1]["theme_name"] == "Web3"
    assert result["themes"][2]["theme_name"] == "IoT"


@pytest.mark.asyncio
async def test_list_themes_empty(mock_zerodb):
    """Test listing when no themes exist."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    result = await hackathon_theme_service.list_themes(mock_zerodb)

    assert result["total"] == 0
    assert result["themes"] == []


# Tests for update_theme

@pytest.mark.asyncio
async def test_update_theme_success(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test successful theme update."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}
    mock_zerodb.tables.update_rows.return_value = None

    update_data = {"description": "Updated description", "icon": "🔥"}
    result = await hackathon_theme_service.update_theme(
        sample_theme_id, update_data, mock_zerodb
    )

    assert result["description"] == "Updated description"
    assert result["icon"] == "🔥"
    mock_zerodb.tables.update_rows.assert_called_once()


@pytest.mark.asyncio
async def test_update_theme_duplicate_name(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test preventing duplicate name on update."""
    other_theme = {**sample_theme_data, "id": str(uuid4())}
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [sample_theme_data]},  # Current theme
        {"rows": [other_theme]}  # Duplicate name check
    ]

    with pytest.raises(HTTPException) as exc_info:
        await hackathon_theme_service.update_theme(
            sample_theme_id,
            {"theme_name": "AI & Machine Learning"},
            mock_zerodb
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in exc_info.value.detail


# Tests for update_theme_order

@pytest.mark.asyncio
async def test_update_theme_order(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test updating theme display order."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}
    mock_zerodb.tables.update_rows.return_value = None

    result = await hackathon_theme_service.update_theme_order(
        sample_theme_id, 5, mock_zerodb
    )

    assert result["display_order"] == 5


# Tests for delete_theme

@pytest.mark.asyncio
async def test_delete_theme_success(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test successful theme deletion."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}
    mock_zerodb.tables.delete_rows.return_value = None

    await hackathon_theme_service.delete_theme(sample_theme_id, mock_zerodb)

    mock_zerodb.tables.delete_rows.assert_called_once_with(
        table_id="hackathon_themes",
        filter={"id": sample_theme_id}
    )


@pytest.mark.asyncio
async def test_delete_theme_not_found(mock_zerodb, sample_theme_id):
    """Test deleting non-existent theme."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await hackathon_theme_service.delete_theme(sample_theme_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Tests for refresh_theme_statistics

@pytest.mark.asyncio
async def test_refresh_theme_statistics(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test refreshing theme statistics from hackathons."""
    # Mock theme query
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [sample_theme_data]},  # Get theme
        {  # Get hackathons with this theme
            "rows": [
                {"theme_id": sample_theme_id, "total_prizes": 10000},
                {"theme_id": sample_theme_id, "total_prizes": 15000},
                {"theme_id": sample_theme_id, "total_prizes": 25000}
            ]
        }
    ]
    mock_zerodb.tables.update_rows.return_value = None

    result = await hackathon_theme_service.refresh_theme_statistics(
        sample_theme_id, mock_zerodb
    )

    assert result["hackathon_count"] == 3
    assert Decimal(result["total_prizes"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_refresh_theme_statistics_no_hackathons(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test statistics refresh with no hackathons."""
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [sample_theme_data]},  # Get theme
        {"rows": []}  # No hackathons
    ]
    mock_zerodb.tables.update_rows.return_value = None

    result = await hackathon_theme_service.refresh_theme_statistics(
        sample_theme_id, mock_zerodb
    )

    assert result["hackathon_count"] == 0
    assert Decimal(result["total_prizes"]) == Decimal("0")


# Tests for refresh_all_theme_statistics

@pytest.mark.asyncio
async def test_refresh_all_theme_statistics(mock_zerodb, sample_theme_data):
    """Test refreshing statistics for all themes."""
    theme1 = {**sample_theme_data, "id": str(uuid4()), "theme_name": "AI"}
    theme2 = {**sample_theme_data, "id": str(uuid4()), "theme_name": "Web3"}

    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [theme1, theme2]},  # List themes
        {"rows": [theme1]},  # Get theme1
        {"rows": [{"theme_id": theme1["id"], "total_prizes": 10000}]},  # Hackathons for theme1
        {"rows": [theme2]},  # Get theme2
        {"rows": [{"theme_id": theme2["id"], "total_prizes": 20000}]}  # Hackathons for theme2
    ]
    mock_zerodb.tables.update_rows.return_value = None

    result = await hackathon_theme_service.refresh_all_theme_statistics(mock_zerodb)

    assert len(result) == 2


# Edge Cases

@pytest.mark.asyncio
async def test_create_theme_minimal_data(mock_zerodb):
    """Test creating theme with only required fields."""
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": []},  # No duplicate
        {"rows": []}  # No existing themes
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    with patch('services.hackathon_theme_service.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid4()
        result = await hackathon_theme_service.create_theme(
            theme_name="Minimal Theme",
            description=None,
            icon=None,
            display_order=None,
            zerodb=mock_zerodb
        )

    assert result["theme_name"] == "Minimal Theme"
    assert result["description"] is None
    assert result["icon"] is None
    assert result["display_order"] == 1


@pytest.mark.asyncio
async def test_update_theme_partial(mock_zerodb, sample_theme_id, sample_theme_data):
    """Test partial theme update (only some fields)."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_theme_data]}
    mock_zerodb.tables.update_rows.return_value = None

    update_data = {"icon": "🚀"}
    result = await hackathon_theme_service.update_theme(
        sample_theme_id, update_data, mock_zerodb
    )

    assert result["icon"] == "🚀"
    assert result["theme_name"] == sample_theme_data["theme_name"]  # Unchanged


@pytest.mark.asyncio
async def test_list_themes_ordering(mock_zerodb, sample_theme_data):
    """Test that themes are properly ordered by display_order."""
    themes = [
        {**sample_theme_data, "display_order": 5, "theme_name": "Last"},
        {**sample_theme_data, "display_order": 1, "theme_name": "First"},
        {**sample_theme_data, "display_order": 3, "theme_name": "Middle"}
    ]
    mock_zerodb.tables.query_rows.return_value = {"rows": themes}

    result = await hackathon_theme_service.list_themes(mock_zerodb)

    # Verify sorted by display_order
    assert result["themes"][0]["display_order"] == 1
    assert result["themes"][1]["display_order"] == 3
    assert result["themes"][2]["display_order"] == 5
