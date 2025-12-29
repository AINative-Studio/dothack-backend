"""
Tests for Authorization Service

Following TDD methodology - tests written before implementation.
Tests role-based access control using ZeroDB hackathon_participants table.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBTimeoutError,
)
from services.authorization import (
    check_builder,
    check_judge,
    check_organizer,
    check_role,
)


class TestCheckRole:
    """Test check_role() function"""

    @pytest.mark.asyncio
    async def test_check_role_success_organizer(self):
        """Should return True when user has organizer role"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": "user-123",
                "hackathon_id": "hack-456",
                "role": "organizer",
            }
        ]

        # Act
        result = await check_role(
            zerodb_client=mock_client,
            user_id="user-123",
            hackathon_id="hack-456",
            required_role="organizer",
        )

        # Assert
        assert result is True
        mock_client.tables.query_rows.assert_called_once_with(
            "hackathon_participants",
            filter={
                "user_id": "user-123",
                "hackathon_id": "hack-456",
            },
        )

    @pytest.mark.asyncio
    async def test_check_role_success_judge(self):
        """Should return True when user has judge role"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": "user-789",
                "hackathon_id": "hack-456",
                "role": "judge",
            }
        ]

        # Act
        result = await check_role(
            zerodb_client=mock_client,
            user_id="user-789",
            hackathon_id="hack-456",
            required_role="judge",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_role_success_builder(self):
        """Should return True when user has builder role"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": "user-999",
                "hackathon_id": "hack-456",
                "role": "builder",
            }
        ]

        # Act
        result = await check_role(
            zerodb_client=mock_client,
            user_id="user-999",
            hackathon_id="hack-456",
            required_role="builder",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_role_forbidden_wrong_role(self):
        """Should raise HTTPException 403 when user has different role"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {
                "user_id": "user-123",
                "hackathon_id": "hack-456",
                "role": "builder",  # User is builder, not organizer
            }
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_role_forbidden_no_participant(self):
        """Should raise HTTPException 403 when user is not participant"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # No rows found

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 403
        assert "not a participant" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_role_handles_zerodb_error(self):
        """Should raise HTTPException 500 on ZeroDB error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("Database error", status_code=500)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 500
        assert "Failed to verify permissions" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_role_handles_timeout(self):
        """Should raise HTTPException 504 on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Request timed out")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 504
        assert "timed out" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_check_role_logs_authorization_failure(self):
        """Should log when authorization fails"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with patch("services.authorization.logger") as mock_logger:
            with pytest.raises(HTTPException):
                await check_role(
                    zerodb_client=mock_client,
                    user_id="user-123",
                    hackathon_id="hack-456",
                    required_role="organizer",
                )

            # Verify logging occurred
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Authorization failed" in call_args
            assert "user-123" in call_args
            assert "hack-456" in call_args


class TestCheckOrganizerHelper:
    """Test check_organizer() helper function"""

    @pytest.mark.asyncio
    async def test_check_organizer_success(self):
        """Should return True for organizer"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-123", "hackathon_id": "hack-456", "role": "organizer"}
        ]

        # Act
        result = await check_organizer(
            zerodb_client=mock_client,
            user_id="user-123",
            hackathon_id="hack-456",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_organizer_forbidden(self):
        """Should raise 403 for non-organizer"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-123", "hackathon_id": "hack-456", "role": "builder"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_organizer(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 403


class TestCheckJudgeHelper:
    """Test check_judge() helper function"""

    @pytest.mark.asyncio
    async def test_check_judge_success(self):
        """Should return True for judge"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-789", "hackathon_id": "hack-456", "role": "judge"}
        ]

        # Act
        result = await check_judge(
            zerodb_client=mock_client,
            user_id="user-789",
            hackathon_id="hack-456",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_judge_forbidden(self):
        """Should raise 403 for non-judge"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-789", "hackathon_id": "hack-456", "role": "builder"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_judge(
                zerodb_client=mock_client,
                user_id="user-789",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 403


class TestCheckBuilderHelper:
    """Test check_builder() helper function"""

    @pytest.mark.asyncio
    async def test_check_builder_success(self):
        """Should return True for builder"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-999", "hackathon_id": "hack-456", "role": "builder"}
        ]

        # Act
        result = await check_builder(
            zerodb_client=mock_client,
            user_id="user-999",
            hackathon_id="hack-456",
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_builder_forbidden(self):
        """Should raise 403 for non-builder"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-999", "hackathon_id": "hack-456", "role": "judge"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_builder(
                zerodb_client=mock_client,
                user_id="user-999",
                hackathon_id="hack-456",
            )

        assert exc_info.value.status_code == 403


class TestPerformanceRequirements:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_check_role_executes_under_100ms(self):
        """Should complete in less than 100ms"""
        import time

        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-123", "hackathon_id": "hack-456", "role": "organizer"}
        ]

        # Act
        start_time = time.time()
        await check_role(
            zerodb_client=mock_client,
            user_id="user-123",
            hackathon_id="hack-456",
            required_role="organizer",
        )
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        # Assert
        assert elapsed_time < 100, f"Execution took {elapsed_time}ms (expected < 100ms)"


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_check_role_with_empty_user_id(self):
        """Should raise 403 for empty user_id"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_check_role_with_empty_hackathon_id(self):
        """Should raise 403 for empty hackathon_id"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_check_role_with_invalid_role(self):
        """Should handle invalid role gracefully"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"user_id": "user-123", "hackathon_id": "hack-456", "role": "invalid_role"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await check_role(
                zerodb_client=mock_client,
                user_id="user-123",
                hackathon_id="hack-456",
                required_role="organizer",
            )

        assert exc_info.value.status_code == 403
