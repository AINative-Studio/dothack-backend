"""
Tests for Team Management Service

Following TDD methodology - tests written before implementation.
Tests team CRUD operations and member management using ZeroDB.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.team_service import (
    add_team_member,
    create_team,
    get_team,
    list_teams,
    remove_team_member,
    update_team,
)


class TestCreateTeam:
    """Test create_team() function"""

    @pytest.mark.asyncio
    async def test_create_team_success(self):
        """Should create team and return team details"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())

        mock_client.tables.insert_rows.return_value = {
            "inserted_ids": [team_id]
        }
        mock_client.tables.query_rows.return_value = [
            {
                "team_id": team_id,
                "hackathon_id": hackathon_id,
                "name": "Team Alpha",
                "track_id": track_id,
                "description": "Building awesome stuff",
                "status": "FORMING",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        # Act
        result = await create_team(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            name="Team Alpha",
            track_id=track_id,
            description="Building awesome stuff",
            creator_id=str(uuid.uuid4())
        )

        # Assert
        assert result["team_id"] == team_id
        assert result["name"] == "Team Alpha"
        assert result["status"] == "FORMING"
        # Should be called twice: once for team, once for creator as LEAD
        assert mock_client.tables.insert_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_create_team_minimal_fields(self):
        """Should create team with only required fields"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_client.tables.insert_rows.return_value = {
            "inserted_ids": [team_id]
        }
        mock_client.tables.query_rows.return_value = [
            {
                "team_id": team_id,
                "hackathon_id": hackathon_id,
                "name": "Team Beta",
                "track_id": None,
                "description": None,
                "status": "FORMING",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        # Act
        result = await create_team(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            name="Team Beta",
            creator_id=str(uuid.uuid4())
        )

        # Assert
        assert result["name"] == "Team Beta"
        assert result["status"] == "FORMING"

    @pytest.mark.asyncio
    async def test_create_team_adds_creator_as_lead(self):
        """Should automatically add creator as team LEAD"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        creator_id = str(uuid.uuid4())

        mock_client.tables.insert_rows.return_value = {
            "inserted_ids": [team_id, str(uuid.uuid4())]
        }
        mock_client.tables.query_rows.return_value = [
            {
                "team_id": team_id,
                "hackathon_id": str(uuid.uuid4()),
                "name": "Team Gamma",
                "status": "FORMING",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        # Act
        await create_team(
            zerodb_client=mock_client,
            hackathon_id=str(uuid.uuid4()),
            name="Team Gamma",
            creator_id=creator_id
        )

        # Assert - Should have called insert_rows twice (team + member)
        assert mock_client.tables.insert_rows.call_count == 2

    @pytest.mark.asyncio
    async def test_create_team_validates_name_not_empty(self):
        """Should raise ValueError for empty team name"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await create_team(
                zerodb_client=mock_client,
                hackathon_id=str(uuid.uuid4()),
                name="",
                creator_id=str(uuid.uuid4())
            )

        assert "name" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_team_handles_zerodb_error(self):
        """Should raise HTTPException 500 on database error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.side_effect = ZeroDBError(
            "Database error", status_code=500
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_team(
                zerodb_client=mock_client,
                hackathon_id=str(uuid.uuid4()),
                name="Team Delta",
                creator_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500


class TestAddTeamMember:
    """Test add_team_member() function"""

    @pytest.mark.asyncio
    async def test_add_team_member_success(self):
        """Should add member to team"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())
        member_id = str(uuid.uuid4())

        # Mock team exists check and duplicate check
        mock_client.tables.query_rows.side_effect = [
            [{"team_id": team_id, "name": "Team Alpha", "status": "FORMING"}],  # Team exists
            []  # No existing member
        ]

        mock_client.tables.insert_rows.return_value = {
            "inserted_ids": [member_id]
        }

        # Act
        result = await add_team_member(
            zerodb_client=mock_client,
            team_id=team_id,
            participant_id=participant_id,
            role="MEMBER",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["team_id"] == team_id
        assert result["participant_id"] == participant_id
        assert result["role"] == "MEMBER"

    @pytest.mark.asyncio
    async def test_add_team_member_with_lead_role(self):
        """Should add member with LEAD role"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        # Mock team exists and no duplicate
        mock_client.tables.query_rows.side_effect = [
            [{"team_id": team_id, "status": "FORMING"}],  # Team exists
            []  # No existing member
        ]
        mock_client.tables.insert_rows.return_value = {
            "inserted_ids": [str(uuid.uuid4())]
        }

        # Act
        result = await add_team_member(
            zerodb_client=mock_client,
            team_id=team_id,
            participant_id=str(uuid.uuid4()),
            role="LEAD",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["role"] == "LEAD"

    @pytest.mark.asyncio
    async def test_add_team_member_validates_role(self):
        """Should raise ValueError for invalid role"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await add_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                role="INVALID_ROLE",
                requester_id=str(uuid.uuid4())
            )

        assert "role" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_team_member_checks_team_exists(self):
        """Should raise HTTPException 404 if team doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                role="MEMBER",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_add_team_member_prevents_duplicate(self):
        """Should raise HTTPException 400 if member already in team"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        # Mock team exists
        mock_client.tables.query_rows.side_effect = [
            [{"team_id": team_id, "status": "FORMING"}],  # Team exists
            [{"participant_id": participant_id}]  # Member already exists
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_team_member(
                zerodb_client=mock_client,
                team_id=team_id,
                participant_id=participant_id,
                role="MEMBER",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 400
        assert "already" in str(exc_info.value.detail).lower()


class TestRemoveTeamMember:
    """Test remove_team_member() function"""

    @pytest.mark.asyncio
    async def test_remove_team_member_success(self):
        """Should remove member from team"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        # Mock member exists
        mock_client.tables.query_rows.return_value = [
            {
                "id": str(uuid.uuid4()),
                "team_id": team_id,
                "participant_id": participant_id,
                "role": "MEMBER"
            }
        ]

        mock_client.tables.delete_row.return_value = {"deleted": True}

        # Act
        result = await remove_team_member(
            zerodb_client=mock_client,
            team_id=team_id,
            participant_id=participant_id,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["success"] is True
        mock_client.tables.delete_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_team_member_not_found(self):
        """Should raise HTTPException 404 if member not in team"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await remove_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_team_member_prevents_last_lead_removal(self):
        """Should prevent removing the last LEAD from team"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        # Mock member is LEAD
        mock_client.tables.query_rows.side_effect = [
            [{"id": str(uuid.uuid4()), "role": "LEAD", "participant_id": participant_id}],
            []  # No other LEADs
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await remove_team_member(
                zerodb_client=mock_client,
                team_id=team_id,
                participant_id=participant_id,
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 400
        assert "lead" in str(exc_info.value.detail).lower()


class TestGetTeam:
    """Test get_team() function"""

    @pytest.mark.asyncio
    async def test_get_team_success(self):
        """Should return team with members"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        mock_client.tables.query_rows.side_effect = [
            # Team query
            [{
                "team_id": team_id,
                "hackathon_id": str(uuid.uuid4()),
                "name": "Team Alpha",
                "status": "ACTIVE",
                "created_at": datetime.utcnow().isoformat()
            }],
            # Members query
            [
                {"participant_id": str(uuid.uuid4()), "role": "LEAD"},
                {"participant_id": str(uuid.uuid4()), "role": "MEMBER"}
            ]
        ]

        # Act
        result = await get_team(
            zerodb_client=mock_client,
            team_id=team_id,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["team_id"] == team_id
        assert result["name"] == "Team Alpha"
        assert len(result["members"]) == 2

    @pytest.mark.asyncio
    async def test_get_team_not_found(self):
        """Should raise HTTPException 404 if team doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_team_includes_member_count(self):
        """Should include member count in response"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        mock_client.tables.query_rows.side_effect = [
            [{"team_id": team_id, "name": "Team Beta"}],
            [
                {"participant_id": str(uuid.uuid4())},
                {"participant_id": str(uuid.uuid4())},
                {"participant_id": str(uuid.uuid4())}
            ]
        ]

        # Act
        result = await get_team(
            zerodb_client=mock_client,
            team_id=team_id,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["member_count"] == 3


class TestListTeams:
    """Test list_teams() function"""

    @pytest.mark.asyncio
    async def test_list_teams_by_hackathon(self):
        """Should return all teams for hackathon"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {
                "team_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "Team Alpha",
                "status": "ACTIVE"
            },
            {
                "team_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "Team Beta",
                "status": "FORMING"
            }
        ]

        # Act
        result = await list_teams(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "Team Alpha"
        assert result[1]["name"] == "Team Beta"

    @pytest.mark.asyncio
    async def test_list_teams_filter_by_status(self):
        """Should filter teams by status"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {
                "team_id": str(uuid.uuid4()),
                "name": "Team Active",
                "status": "ACTIVE"
            }
        ]

        # Act
        result = await list_teams(
            zerodb_client=mock_client,
            hackathon_id=hackathon_id,
            status="ACTIVE",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert len(result) == 1
        assert result[0]["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_list_teams_pagination(self):
        """Should support pagination"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act
        await list_teams(
            zerodb_client=mock_client,
            hackathon_id=str(uuid.uuid4()),
            skip=10,
            limit=20,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        call_args = mock_client.tables.query_rows.call_args
        assert call_args.kwargs.get("skip") == 10
        assert call_args.kwargs.get("limit") == 20

    @pytest.mark.asyncio
    async def test_list_teams_empty_result(self):
        """Should return empty list if no teams"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act
        result = await list_teams(
            zerodb_client=mock_client,
            hackathon_id=str(uuid.uuid4()),
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result == []


class TestUpdateTeam:
    """Test update_team() function"""

    @pytest.mark.asyncio
    async def test_update_team_name(self):
        """Should update team name"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"team_id": team_id, "name": "Old Name"}
        ]
        mock_client.tables.update_row.return_value = {
            "team_id": team_id,
            "name": "New Name"
        }

        # Act
        result = await update_team(
            zerodb_client=mock_client,
            team_id=team_id,
            name="New Name",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_team_status(self):
        """Should update team status"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"team_id": team_id, "status": "FORMING"}
        ]
        mock_client.tables.update_row.return_value = {
            "team_id": team_id,
            "status": "ACTIVE"
        }

        # Act
        result = await update_team(
            zerodb_client=mock_client,
            team_id=team_id,
            status="ACTIVE",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_update_team_validates_status(self):
        """Should validate status values"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await update_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                status="INVALID_STATUS",
                requester_id=str(uuid.uuid4())
            )

        assert "status" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_team_multiple_fields(self):
        """Should update multiple fields at once"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"team_id": team_id}
        ]
        mock_client.tables.update_row.return_value = {
            "team_id": team_id,
            "name": "Updated Team",
            "description": "New description",
            "status": "ACTIVE"
        }

        # Act
        result = await update_team(
            zerodb_client=mock_client,
            team_id=team_id,
            name="Updated Team",
            description="New description",
            status="ACTIVE",
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert result["name"] == "Updated Team"
        assert result["description"] == "New description"
        assert result["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_update_team_not_found(self):
        """Should raise HTTPException 404 if team doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                name="New Name",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 404


class TestErrorHandling:
    """Test error handling across all functions"""

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self):
        """Should raise HTTPException 504 on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_handles_database_error(self):
        """Should raise HTTPException 500 on database error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError(
            "Database error", status_code=500
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_teams(
                zerodb_client=mock_client,
                hackathon_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500


class TestAuthorizationIntegration:
    """Test authorization checks in team operations"""

    @pytest.mark.asyncio
    async def test_add_member_checks_authorization(self):
        """Should verify requester has permission to add members"""
        # This will be implemented with authorization service integration
        # Placeholder for future authorization checks
        pass

    @pytest.mark.asyncio
    async def test_remove_member_checks_authorization(self):
        """Should verify requester has permission to remove members"""
        # This will be implemented with authorization service integration
        # Placeholder for future authorization checks
        pass

    @pytest.mark.asyncio
    async def test_update_team_checks_authorization(self):
        """Should verify requester has permission to update team"""
        # This will be implemented with authorization service integration
        # Placeholder for future authorization checks
        pass


class TestPerformanceRequirements:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_list_teams_handles_large_result(self):
        """Should handle large number of teams efficiently"""
        # Arrange
        mock_client = AsyncMock()
        teams = [
            {"team_id": str(uuid.uuid4()), "name": f"Team {i}"}
            for i in range(100)
        ]
        mock_client.tables.query_rows.return_value = teams

        # Act
        result = await list_teams(
            zerodb_client=mock_client,
            hackathon_id=str(uuid.uuid4()),
            limit=100,
            requester_id=str(uuid.uuid4())
        )

        # Assert
        assert len(result) == 100


class TestEdgeCasesAndCoverage:
    """Additional edge cases to improve coverage"""

    @pytest.mark.asyncio
    async def test_create_team_unexpected_error(self):
        """Should handle unexpected errors gracefully"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_team(
                zerodb_client=mock_client,
                hackathon_id=str(uuid.uuid4()),
                name="Team Test",
                creator_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_add_team_member_unexpected_error(self):
        """Should handle unexpected errors in add_team_member"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                role="MEMBER",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_remove_team_member_unexpected_error(self):
        """Should handle unexpected errors in remove_team_member"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await remove_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_team_unexpected_error(self):
        """Should handle unexpected errors in get_team"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_update_team_unexpected_error(self):
        """Should handle unexpected errors in update_team"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                name="New Name",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_create_team_timeout_error(self):
        """Should handle timeout in create_team"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.insert_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_team(
                zerodb_client=mock_client,
                hackathon_id=str(uuid.uuid4()),
                name="Team Test",
                creator_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_add_team_member_timeout_error(self):
        """Should handle timeout in add_team_member"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await add_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                role="MEMBER",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_remove_team_member_timeout_error(self):
        """Should handle timeout in remove_team_member"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await remove_team_member(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                participant_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_update_team_timeout_error(self):
        """Should handle timeout in update_team"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_team(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                name="New Name",
                requester_id=str(uuid.uuid4())
            )

        assert exc_info.value.status_code == 504
