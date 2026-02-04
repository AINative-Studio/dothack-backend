"""
Comprehensive test suite for Projects API.

Tests CRUD operations, status management, authorization, and edge cases.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException, status
from services import project_service


# Test Fixtures

@pytest.fixture
def mock_zerodb():
    """Mock ZeroDB client."""
    mock = AsyncMock()
    mock.tables = AsyncMock()
    return mock


@pytest.fixture
def sample_project_id():
    """Sample project UUID."""
    return str(uuid4())


@pytest.fixture
def sample_hackathon_id():
    """Sample hackathon UUID."""
    return str(uuid4())


@pytest.fixture
def sample_team_id():
    """Sample team UUID."""
    return str(uuid4())


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return str(uuid4())


@pytest.fixture
def sample_project_data(sample_project_id, sample_hackathon_id, sample_team_id):
    """Sample project data."""
    return {
        "project_id": sample_project_id,
        "hackathon_id": sample_hackathon_id,
        "team_id": sample_team_id,
        "title": "AI-Powered Code Review",
        "one_liner": "Automated code review using machine learning",
        "description": "A comprehensive tool for automated code quality analysis",
        "status": "IDEA",
        "repo_url": "https://github.com/team/project",
        "demo_url": "https://demo.example.com",
        "video_url": "https://youtube.com/watch?v=demo",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_team_data(sample_team_id, sample_hackathon_id):
    """Sample team data."""
    return {
        "team_id": sample_team_id,
        "hackathon_id": sample_hackathon_id,
        "name": "Team Alpha",
        "status": "ACTIVE"
    }


@pytest.fixture
def sample_member_data(sample_team_id, sample_user_id):
    """Sample team member data."""
    return {
        "id": str(uuid4()),
        "team_id": sample_team_id,
        "participant_id": sample_user_id,
        "role": "LEAD"
    }


# Tests for create_project

@pytest.mark.asyncio
async def test_create_project_success(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_team_data
):
    """Test successful project creation."""
    # Mock no existing project
    mock_zerodb.tables.query_rows.side_effect = [
        [],  # No existing project
        [sample_team_data],  # Team exists
        [{  # Return created project
            "project_id": "new-proj-id",
            "hackathon_id": sample_hackathon_id,
            "team_id": sample_team_id,
            "title": "New Project",
            "status": "IDEA"
        }]
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    result = await project_service.create_project(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        team_id=sample_team_id,
        title="New Project",
        creator_id=sample_user_id
    )

    assert result["title"] == "New Project"
    assert result["status"] == "IDEA"
    mock_zerodb.tables.insert_rows.assert_called_once()


@pytest.mark.asyncio
async def test_create_project_with_all_fields(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_team_data
):
    """Test project creation with all optional fields."""
    mock_zerodb.tables.query_rows.side_effect = [
        [],  # No existing project
        [sample_team_data],  # Team exists
        [{  # Return created project
            "project_id": "new-proj-id",
            "hackathon_id": sample_hackathon_id,
            "team_id": sample_team_id,
            "title": "Full Project",
            "one_liner": "Short desc",
            "description": "Long desc",
            "repo_url": "https://github.com/repo",
            "demo_url": "https://demo.com",
            "video_url": "https://youtube.com/video",
            "status": "IDEA"
        }]
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    result = await project_service.create_project(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        team_id=sample_team_id,
        title="Full Project",
        creator_id=sample_user_id,
        one_liner="Short desc",
        description="Long desc",
        repo_url="https://github.com/repo",
        demo_url="https://demo.com",
        video_url="https://youtube.com/video"
    )

    assert result["one_liner"] == "Short desc"
    assert result["repo_url"] == "https://github.com/repo"


@pytest.mark.asyncio
async def test_create_project_duplicate(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_project_data
):
    """Test preventing duplicate project for team."""
    # Mock existing project
    mock_zerodb.tables.query_rows.return_value = [sample_project_data]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.create_project(
            zerodb_client=mock_zerodb,
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Duplicate Project",
            creator_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already has a project" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_project_team_not_found(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id
):
    """Test project creation when team doesn't exist."""
    mock_zerodb.tables.query_rows.side_effect = [
        [],  # No existing project
        []   # Team not found
    ]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.create_project(
            zerodb_client=mock_zerodb,
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="Project",
            creator_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_project_empty_title(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id
):
    """Test project creation with empty title."""
    with pytest.raises(ValueError) as exc_info:
        await project_service.create_project(
            zerodb_client=mock_zerodb,
            hackathon_id=sample_hackathon_id,
            team_id=sample_team_id,
            title="   ",  # Whitespace only
            creator_id=sample_user_id
        )

    assert "cannot be empty" in str(exc_info.value)


# Tests for get_project

@pytest.mark.asyncio
async def test_get_project_success(
    mock_zerodb, sample_project_id, sample_user_id, sample_project_data
):
    """Test successful project retrieval."""
    mock_zerodb.tables.query_rows.return_value = [sample_project_data]

    result = await project_service.get_project(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        requester_id=sample_user_id
    )

    assert result == sample_project_data
    mock_zerodb.tables.query_rows.assert_called_once_with(
        "projects",
        filter={"project_id": sample_project_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_get_project_not_found(mock_zerodb, sample_project_id, sample_user_id):
    """Test project not found."""
    mock_zerodb.tables.query_rows.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        await project_service.get_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


# Tests for list_projects

@pytest.mark.asyncio
async def test_list_projects_success(
    mock_zerodb, sample_hackathon_id, sample_user_id, sample_project_data
):
    """Test listing all projects for a hackathon."""
    projects = [
        {**sample_project_data, "title": "Project 1", "status": "IDEA"},
        {**sample_project_data, "title": "Project 2", "status": "BUILDING"},
        {**sample_project_data, "title": "Project 3", "status": "SUBMITTED"}
    ]
    mock_zerodb.tables.query_rows.return_value = projects

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id
    )

    assert len(result) == 3
    assert result[0]["title"] == "Project 1"


@pytest.mark.asyncio
async def test_list_projects_with_status_filter(
    mock_zerodb, sample_hackathon_id, sample_user_id, sample_project_data
):
    """Test listing projects with status filter."""
    projects = [
        {**sample_project_data, "title": "Submitted 1", "status": "SUBMITTED"},
        {**sample_project_data, "title": "Submitted 2", "status": "SUBMITTED"}
    ]
    mock_zerodb.tables.query_rows.return_value = projects

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id,
        status="SUBMITTED"
    )

    assert len(result) == 2
    assert all(p["status"] == "SUBMITTED" for p in result)


@pytest.mark.asyncio
async def test_list_projects_with_team_filter(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_project_data
):
    """Test listing projects with team filter."""
    mock_zerodb.tables.query_rows.return_value = [sample_project_data]

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id,
        team_id=sample_team_id
    )

    assert len(result) == 1
    assert result[0]["team_id"] == sample_team_id


@pytest.mark.asyncio
async def test_list_projects_empty(mock_zerodb, sample_hackathon_id, sample_user_id):
    """Test listing when no projects exist."""
    mock_zerodb.tables.query_rows.return_value = []

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id
    )

    assert result == []


@pytest.mark.asyncio
async def test_list_projects_pagination(
    mock_zerodb, sample_hackathon_id, sample_user_id, sample_project_data
):
    """Test project listing with pagination."""
    projects = [sample_project_data]
    mock_zerodb.tables.query_rows.return_value = projects

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id,
        skip=10,
        limit=50
    )

    mock_zerodb.tables.query_rows.assert_called_once()
    call_args = mock_zerodb.tables.query_rows.call_args
    assert call_args.kwargs["skip"] == 10
    assert call_args.kwargs["limit"] == 50


# Tests for update_project

@pytest.mark.asyncio
async def test_update_project_success(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test successful project update."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        [sample_member_data]    # User is team member
    ]
    mock_zerodb.tables.update_row.return_value = {
        **sample_project_data,
        "title": "Updated Title",
        "description": "Updated description"
    }

    result = await project_service.update_project(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        requester_id=sample_user_id,
        title="Updated Title",
        description="Updated description"
    )

    assert result["title"] == "Updated Title"
    assert result["description"] == "Updated description"
    mock_zerodb.tables.update_row.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_partial(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test partial project update (only some fields)."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],
        [sample_member_data]
    ]
    mock_zerodb.tables.update_row.return_value = {
        **sample_project_data,
        "repo_url": "https://github.com/new/repo"
    }

    result = await project_service.update_project(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        requester_id=sample_user_id,
        repo_url="https://github.com/new/repo"
    )

    assert result["repo_url"] == "https://github.com/new/repo"


@pytest.mark.asyncio
async def test_update_project_not_team_member(
    mock_zerodb, sample_project_id, sample_user_id, sample_project_data
):
    """Test update fails when user is not a team member."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        []                       # User not in team
    ]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.update_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id,
            title="New Title"
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "team members" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_project_not_found(mock_zerodb, sample_project_id, sample_user_id):
    """Test updating non-existent project."""
    mock_zerodb.tables.query_rows.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        await project_service.update_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id,
            title="New Title"
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_project_empty_title(
    mock_zerodb, sample_project_id, sample_user_id
):
    """Test update with empty title."""
    with pytest.raises(ValueError) as exc_info:
        await project_service.update_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id,
            title="   "  # Whitespace only
        )

    assert "cannot be empty" in str(exc_info.value)


# Tests for update_project_status

@pytest.mark.asyncio
async def test_update_project_status_success(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test successful status update."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        [sample_member_data]    # User is team member
    ]
    mock_zerodb.tables.update_row.return_value = {
        **sample_project_data,
        "status": "BUILDING"
    }

    result = await project_service.update_project_status(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        status="BUILDING",
        requester_id=sample_user_id
    )

    assert result["status"] == "BUILDING"


@pytest.mark.asyncio
async def test_update_project_status_to_submitted(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test updating status to SUBMITTED."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],
        [sample_member_data]
    ]
    mock_zerodb.tables.update_row.return_value = {
        **sample_project_data,
        "status": "SUBMITTED"
    }

    result = await project_service.update_project_status(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        status="SUBMITTED",
        requester_id=sample_user_id
    )

    assert result["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_update_project_status_invalid(
    mock_zerodb, sample_project_id, sample_user_id
):
    """Test updating to invalid status."""
    with pytest.raises(ValueError) as exc_info:
        await project_service.update_project_status(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            status="INVALID_STATUS",
            requester_id=sample_user_id
        )

    assert "Invalid status" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_project_status_not_team_member(
    mock_zerodb, sample_project_id, sample_user_id, sample_project_data
):
    """Test status update fails when user is not a team member."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        []                       # User not in team
    ]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.update_project_status(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            status="BUILDING",
            requester_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# Tests for delete_project

@pytest.mark.asyncio
async def test_delete_project_success(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test successful project deletion."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        [sample_member_data]    # User is team member
    ]
    mock_zerodb.tables.delete_row.return_value = None

    result = await project_service.delete_project(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        requester_id=sample_user_id
    )

    assert result["success"] is True
    mock_zerodb.tables.delete_row.assert_called_once_with("projects", sample_project_id)


@pytest.mark.asyncio
async def test_delete_project_not_team_member(
    mock_zerodb, sample_project_id, sample_user_id, sample_project_data
):
    """Test deletion fails when user is not a team member."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],  # Project exists
        []                       # User not in team
    ]

    with pytest.raises(HTTPException) as exc_info:
        await project_service.delete_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "team members" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_project_not_found(mock_zerodb, sample_project_id, sample_user_id):
    """Test deleting non-existent project."""
    mock_zerodb.tables.query_rows.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        await project_service.delete_project(
            zerodb_client=mock_zerodb,
            project_id=sample_project_id,
            requester_id=sample_user_id
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Tests for get_team_project

@pytest.mark.asyncio
async def test_get_team_project_success(
    mock_zerodb, sample_team_id, sample_user_id, sample_project_data
):
    """Test getting team's project."""
    mock_zerodb.tables.query_rows.return_value = [sample_project_data]

    result = await project_service.get_team_project(
        zerodb_client=mock_zerodb,
        team_id=sample_team_id,
        requester_id=sample_user_id
    )

    assert result == sample_project_data
    mock_zerodb.tables.query_rows.assert_called_once_with(
        "projects",
        filter={"team_id": sample_team_id},
        limit=1
    )


@pytest.mark.asyncio
async def test_get_team_project_no_project(mock_zerodb, sample_team_id, sample_user_id):
    """Test getting team project when team has no project."""
    mock_zerodb.tables.query_rows.return_value = []

    result = await project_service.get_team_project(
        zerodb_client=mock_zerodb,
        team_id=sample_team_id,
        requester_id=sample_user_id
    )

    assert result is None


# Edge Cases and Authorization Tests

@pytest.mark.asyncio
async def test_create_project_minimal_data(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_team_data
):
    """Test creating project with only required fields."""
    mock_zerodb.tables.query_rows.side_effect = [
        [],  # No existing project
        [sample_team_data],  # Team exists
        [{
            "project_id": "min-proj-id",
            "hackathon_id": sample_hackathon_id,
            "team_id": sample_team_id,
            "title": "Minimal Project",
            "status": "IDEA"
        }]
    ]
    mock_zerodb.tables.insert_rows.return_value = None

    result = await project_service.create_project(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        team_id=sample_team_id,
        title="Minimal Project",
        creator_id=sample_user_id
    )

    assert result["title"] == "Minimal Project"
    assert result["status"] == "IDEA"


@pytest.mark.asyncio
async def test_list_projects_multiple_filters(
    mock_zerodb, sample_hackathon_id, sample_team_id, sample_user_id, sample_project_data
):
    """Test listing projects with multiple filters."""
    mock_zerodb.tables.query_rows.return_value = [sample_project_data]

    result = await project_service.list_projects(
        zerodb_client=mock_zerodb,
        hackathon_id=sample_hackathon_id,
        requester_id=sample_user_id,
        status="SUBMITTED",
        team_id=sample_team_id
    )

    call_args = mock_zerodb.tables.query_rows.call_args
    assert call_args.kwargs["filter"]["status"] == "SUBMITTED"
    assert call_args.kwargs["filter"]["team_id"] == sample_team_id


@pytest.mark.asyncio
async def test_update_all_project_fields(
    mock_zerodb, sample_project_id, sample_team_id, sample_user_id,
    sample_project_data, sample_member_data
):
    """Test updating all project fields at once."""
    mock_zerodb.tables.query_rows.side_effect = [
        [sample_project_data],
        [sample_member_data]
    ]
    mock_zerodb.tables.update_row.return_value = {
        **sample_project_data,
        "title": "New Title",
        "one_liner": "New liner",
        "description": "New desc",
        "repo_url": "https://github.com/new",
        "demo_url": "https://demo.new",
        "video_url": "https://video.new"
    }

    result = await project_service.update_project(
        zerodb_client=mock_zerodb,
        project_id=sample_project_id,
        requester_id=sample_user_id,
        title="New Title",
        one_liner="New liner",
        description="New desc",
        repo_url="https://github.com/new",
        demo_url="https://demo.new",
        video_url="https://video.new"
    )

    assert result["title"] == "New Title"
    assert result["repo_url"] == "https://github.com/new"
