"""
Comprehensive test suite for Projects API.

Tests CRUD operations, status transitions, authorization, and validation.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import HTTPException, status
from services import project_service
from api.schemas.project import ProjectStatus


# Test Fixtures

@pytest.fixture
def mock_zerodb():
    """Mock ZeroDB client."""
    mock = AsyncMock()
    mock.tables = AsyncMock()
    return mock


@pytest.fixture
def sample_hackathon_id():
    """Sample hackathon UUID."""
    return str(uuid4())


@pytest.fixture
def sample_team_id():
    """Sample team UUID."""
    return str(uuid4())


@pytest.fixture
def sample_project_id():
    """Sample project UUID."""
    return str(uuid4())


@pytest.fixture
def sample_project_data(sample_project_id, sample_hackathon_id, sample_team_id):
    """Sample project data."""
    return {
        "project_id": sample_project_id,
        "hackathon_id": sample_hackathon_id,
        "team_id": sample_team_id,
        "title": "AI-Powered Code Review Tool",
        "one_liner": "Automated code quality analysis using ML",
        "status": "IDEA",
        "repo_url": "https://github.com/example/ai-review",
        "demo_url": "https://demo.example.com",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


# Tests for verify_hackathon_exists

@pytest.mark.asyncio
async def test_verify_hackathon_exists_success(mock_zerodb, sample_hackathon_id):
    """Test successful hackathon verification."""
    mock_zerodb.tables.query_rows.return_value = {
        "rows": [{"hackathon_id": sample_hackathon_id}]
    }

    await project_service.verify_hackathon_exists(sample_hackathon_id, mock_zerodb)

    mock_zerodb.tables.query_rows.assert_called_once_with(
        table_id="hackathons",
        filter={"hackathon_id": sample_hackathon_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_verify_hackathon_exists_not_found(mock_zerodb, sample_hackathon_id):
    """Test hackathon not found."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.verify_hackathon_exists(sample_hackathon_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


# Tests for verify_team_exists

@pytest.mark.asyncio
async def test_verify_team_exists_success(mock_zerodb, sample_team_id, sample_hackathon_id):
    """Test successful team verification."""
    mock_zerodb.tables.query_rows.return_value = {
        "rows": [{"team_id": sample_team_id, "hackathon_id": sample_hackathon_id}]
    }

    await project_service.verify_team_exists(sample_team_id, sample_hackathon_id, mock_zerodb)

    mock_zerodb.tables.query_rows.assert_called_once_with(
        table_id="teams",
        filter={"team_id": sample_team_id, "hackathon_id": sample_hackathon_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_verify_team_exists_not_found(mock_zerodb, sample_team_id, sample_hackathon_id):
    """Test team not found in hackathon."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.verify_team_exists(sample_team_id, sample_hackathon_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found in hackathon" in exc_info.value.detail


# Tests for check_existing_project

@pytest.mark.asyncio
async def test_check_existing_project_found(mock_zerodb, sample_team_id, sample_hackathon_id, sample_project_data):
    """Test finding existing project for team."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    result = await project_service.check_existing_project(sample_team_id, sample_hackathon_id, mock_zerodb)

    assert result == sample_project_data


@pytest.mark.asyncio
async def test_check_existing_project_not_found(mock_zerodb, sample_team_id, sample_hackathon_id):
    """Test no existing project for team."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    result = await project_service.check_existing_project(sample_team_id, sample_hackathon_id, mock_zerodb)

    assert result is None


@pytest.mark.asyncio
async def test_check_existing_project_exclude(mock_zerodb, sample_team_id, sample_hackathon_id, sample_project_id, sample_project_data):
    """Test excluding specific project from check."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    result = await project_service.check_existing_project(
        sample_team_id, sample_hackathon_id, mock_zerodb, exclude_project_id=sample_project_id
    )

    assert result is None


# Tests for validate_status_transition

@pytest.mark.asyncio
async def test_validate_status_transition_idea_to_building():
    """Test valid IDEA → BUILDING transition."""
    await project_service.validate_status_transition("IDEA", "BUILDING")


@pytest.mark.asyncio
async def test_validate_status_transition_building_to_submitted():
    """Test valid BUILDING → SUBMITTED transition."""
    await project_service.validate_status_transition("BUILDING", "SUBMITTED")


@pytest.mark.asyncio
async def test_validate_status_transition_invalid():
    """Test invalid status transition."""
    with pytest.raises(HTTPException) as exc_info:
        await project_service.validate_status_transition("IDEA", "SUBMITTED")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot transition" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_status_transition_from_submitted():
    """Test that SUBMITTED is terminal state."""
    with pytest.raises(HTTPException) as exc_info:
        await project_service.validate_status_transition("SUBMITTED", "BUILDING")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "terminal state" in exc_info.value.detail


# Tests for create_project

@pytest.mark.asyncio
async def test_create_project_success(mock_zerodb, sample_hackathon_id, sample_team_id):
    """Test successful project creation."""
    # Mock successful verifications and no existing project
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [{"hackathon_id": sample_hackathon_id}]},  # hackathon exists
        {"rows": [{"team_id": sample_team_id}]},  # team exists
        {"rows": []}  # no existing project
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    with patch('services.project_service.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid4()
        result = await project_service.create_project(
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Test Project",
            one_liner="Test description",
            repo_url="https://github.com/test/repo",
            demo_url="https://demo.test.com",
            zerodb=mock_zerodb
        )

    assert result["title"] == "Test Project"
    assert result["status"] == "IDEA"
    assert result["hackathon_id"] == sample_hackathon_id
    assert result["team_id"] == sample_team_id
    mock_zerodb.tables.insert_rows.assert_called_once()


@pytest.mark.asyncio
async def test_create_project_duplicate(mock_zerodb, sample_hackathon_id, sample_team_id, sample_project_data):
    """Test preventing duplicate project creation."""
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [{"hackathon_id": sample_hackathon_id}]},  # hackathon exists
        {"rows": [{"team_id": sample_team_id}]},  # team exists
        {"rows": [sample_project_data]}  # existing project found
    ]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.create_project(
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Test Project",
            one_liner=None,
            repo_url=None,
            demo_url=None,
            zerodb=mock_zerodb
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already has a project" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_project_hackathon_not_found(mock_zerodb, sample_hackathon_id, sample_team_id):
    """Test project creation with non-existent hackathon."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.create_project(
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Test Project",
            one_liner=None,
            repo_url=None,
            demo_url=None,
            zerodb=mock_zerodb
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Tests for get_project

@pytest.mark.asyncio
async def test_get_project_success(mock_zerodb, sample_project_id, sample_project_data):
    """Test successful project retrieval."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    result = await project_service.get_project(sample_project_id, mock_zerodb)

    assert result == sample_project_data
    mock_zerodb.tables.query_rows.assert_called_once_with(
        table_id="projects",
        filter={"project_id": sample_project_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_get_project_not_found(mock_zerodb, sample_project_id):
    """Test project not found."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.get_project(sample_project_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


# Tests for list_projects

@pytest.mark.asyncio
async def test_list_projects_all(mock_zerodb, sample_hackathon_id, sample_project_data):
    """Test listing all projects in hackathon."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data] * 3}

    result = await project_service.list_projects(
        hackathon_id=sample_hackathon_id,
        status_filter=None,
        skip=0,
        limit=10,
        zerodb=mock_zerodb
    )

    assert result["total"] == 3
    assert len(result["projects"]) == 3
    assert result["skip"] == 0
    assert result["limit"] == 10


@pytest.mark.asyncio
async def test_list_projects_with_status_filter(mock_zerodb, sample_hackathon_id, sample_project_data):
    """Test listing projects with status filter."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    result = await project_service.list_projects(
        hackathon_id=sample_hackathon_id,
        status_filter="IDEA",
        skip=0,
        limit=10,
        zerodb=mock_zerodb
    )

    assert result["total"] == 1
    mock_zerodb.tables.query_rows.assert_called_once()
    call_args = mock_zerodb.tables.query_rows.call_args
    assert call_args[1]["filter"]["status"] == "IDEA"


@pytest.mark.asyncio
async def test_list_projects_pagination(mock_zerodb, sample_hackathon_id, sample_project_data):
    """Test pagination of project list."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data] * 5}

    result = await project_service.list_projects(
        hackathon_id=sample_hackathon_id,
        status_filter=None,
        skip=2,
        limit=2,
        zerodb=mock_zerodb
    )

    assert result["total"] == 5
    assert len(result["projects"]) == 2


# Tests for get_team_project

@pytest.mark.asyncio
async def test_get_team_project_found(mock_zerodb, sample_team_id, sample_hackathon_id, sample_project_data):
    """Test getting team's project."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    result = await project_service.get_team_project(sample_team_id, sample_hackathon_id, mock_zerodb)

    assert result == sample_project_data


@pytest.mark.asyncio
async def test_get_team_project_not_found(mock_zerodb, sample_team_id, sample_hackathon_id):
    """Test team has no project."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    result = await project_service.get_team_project(sample_team_id, sample_hackathon_id, mock_zerodb)

    assert result is None


# Tests for update_project

@pytest.mark.asyncio
async def test_update_project_success(mock_zerodb, sample_project_id, sample_project_data):
    """Test successful project update."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}
    mock_zerodb.tables.update_rows.return_value = None

    update_data = {"title": "Updated Title", "repo_url": "https://github.com/updated/repo"}
    result = await project_service.update_project(sample_project_id, update_data, mock_zerodb)

    assert result["title"] == "Updated Title"
    assert result["repo_url"] == "https://github.com/updated/repo"
    mock_zerodb.tables.update_rows.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_not_found(mock_zerodb, sample_project_id):
    """Test updating non-existent project."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.update_project(sample_project_id, {"title": "New"}, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Tests for update_project_status

@pytest.mark.asyncio
async def test_update_project_status_success(mock_zerodb, sample_project_id, sample_project_data):
    """Test successful status update."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}
    mock_zerodb.tables.update_rows.return_value = None

    result = await project_service.update_project_status(sample_project_id, "BUILDING", mock_zerodb)

    assert result["status"] == "BUILDING"


@pytest.mark.asyncio
async def test_update_project_status_invalid_transition(mock_zerodb, sample_project_id, sample_project_data):
    """Test invalid status transition."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.update_project_status(sample_project_id, "SUBMITTED", mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot transition" in exc_info.value.detail


# Tests for delete_project

@pytest.mark.asyncio
async def test_delete_project_success(mock_zerodb, sample_project_id, sample_project_data):
    """Test successful project deletion."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}
    mock_zerodb.tables.delete_rows.return_value = None

    await project_service.delete_project(sample_project_id, mock_zerodb)

    mock_zerodb.tables.delete_rows.assert_called_once_with(
        table_id="projects",
        filter={"project_id": sample_project_id}
    )


@pytest.mark.asyncio
async def test_delete_project_not_found(mock_zerodb, sample_project_id):
    """Test deleting non-existent project."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    with pytest.raises(HTTPException) as exc_info:
        await project_service.delete_project(sample_project_id, mock_zerodb)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Edge Cases and Error Handling

@pytest.mark.asyncio
async def test_create_project_minimal_data(mock_zerodb, sample_hackathon_id, sample_team_id):
    """Test creating project with only required fields."""
    mock_zerodb.tables.query_rows.side_effect = [
        {"rows": [{"hackathon_id": sample_hackathon_id}]},
        {"rows": [{"team_id": sample_team_id}]},
        {"rows": []}
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    with patch('services.project_service.uuid4') as mock_uuid:
        mock_uuid.return_value = uuid4()
        result = await project_service.create_project(
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Minimal Project",
            one_liner=None,
            repo_url=None,
            demo_url=None,
            zerodb=mock_zerodb
        )

    assert result["title"] == "Minimal Project"
    assert result["one_liner"] is None
    assert result["repo_url"] is None
    assert result["demo_url"] is None


@pytest.mark.asyncio
async def test_update_project_partial_update(mock_zerodb, sample_project_id, sample_project_data):
    """Test partial project update (only some fields)."""
    mock_zerodb.tables.query_rows.return_value = {"rows": [sample_project_data]}
    mock_zerodb.tables.update_rows.return_value = None

    update_data = {"demo_url": "https://new-demo.example.com"}
    result = await project_service.update_project(sample_project_id, update_data, mock_zerodb)

    assert result["demo_url"] == "https://new-demo.example.com"
    assert result["title"] == sample_project_data["title"]  # Unchanged


@pytest.mark.asyncio
async def test_list_projects_empty_hackathon(mock_zerodb, sample_hackathon_id):
    """Test listing projects in hackathon with no projects."""
    mock_zerodb.tables.query_rows.return_value = {"rows": []}

    result = await project_service.list_projects(
        hackathon_id=sample_hackathon_id,
        status_filter=None,
        skip=0,
        limit=10,
        zerodb=mock_zerodb
    )

    assert result["total"] == 0
    assert result["projects"] == []
