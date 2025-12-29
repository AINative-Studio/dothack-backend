"""
ZeroDB Tables API Wrapper

Provides methods for NoSQL table operations.
"""

from typing import Any, List, Optional


class TablesAPI:
    """
    Wrapper for ZeroDB Tables API operations.

    Provides methods for:
    - Creating tables
    - Listing tables
    - Getting table details
    - Deleting tables
    - CRUD operations on table rows
    """

    def __init__(self, client):
        """
        Initialize TablesAPI wrapper.

        Args:
            client: ZeroDBClient instance
        """
        self.client = client

    async def create(
        self,
        name: str,
        schema: dict[str, Any],
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new table.

        Args:
            name: Table name
            schema: Table schema definition
            description: Optional table description

        Returns:
            Dict with table details

        Example:
            schema = {
                "fields": {
                    "id": {"type": "uuid", "primary_key": True},
                    "name": {"type": "text", "required": True}
                }
            }
            table = await client.tables.create("users", schema)
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables"
        payload = {"name": name, "schema": schema}
        if description:
            payload["description"] = description

        return await self.client._request("POST", path, json=payload)

    async def list(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """
        List all tables in the project.

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of table objects
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables"
        params = {"skip": skip, "limit": limit}
        response = await self.client._request("GET", path, params=params)
        return response.get("tables", [])

    async def get(self, table_name: str) -> dict[str, Any]:
        """
        Get table details.

        Args:
            table_name: Name of the table

        Returns:
            Dict with table details including schema
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}"
        return await self.client._request("GET", path)

    async def delete(self, table_name: str) -> dict[str, Any]:
        """
        Delete a table.

        Args:
            table_name: Name of the table to delete

        Returns:
            Dict with deletion confirmation
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}"
        return await self.client._request("DELETE", path)

    async def insert_rows(
        self,
        table_name: str,
        rows: List[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Insert rows into a table.

        Args:
            table_name: Name of the table
            rows: List of row objects to insert

        Returns:
            Dict with inserted row IDs

        Example:
            rows = [
                {"id": "uuid1", "name": "Alice"},
                {"id": "uuid2", "name": "Bob"}
            ]
            result = await client.tables.insert_rows("users", rows)
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}/rows"
        payload = {"rows": rows}
        return await self.client._request("POST", path, json=payload)

    async def query_rows(
        self,
        table_name: str,
        filter: Optional[dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict[str, Any]]:
        """
        Query rows from a table.

        Args:
            table_name: Name of the table
            filter: MongoDB-style query filter (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching rows

        Example:
            rows = await client.tables.query_rows(
                "users",
                filter={"status": "active"},
                limit=10
            )
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}/rows"
        params = {"skip": skip, "limit": limit}
        if filter:
            params["filter"] = filter

        response = await self.client._request("GET", path, params=params)
        return response.get("rows", [])

    async def update_row(
        self,
        table_name: str,
        row_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update a row in a table.

        Args:
            table_name: Name of the table
            row_id: ID of the row to update
            data: Updated data

        Returns:
            Dict with updated row
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}/rows/{row_id}"
        payload = {"data": data}
        return await self.client._request("PUT", path, json=payload)

    async def delete_row(self, table_name: str, row_id: str) -> dict[str, Any]:
        """
        Delete a row from a table.

        Args:
            table_name: Name of the table
            row_id: ID of the row to delete

        Returns:
            Dict with deletion confirmation
        """
        path = f"/v1/public/projects/{self.client.project_id}/database/tables/{table_name}/rows/{row_id}"
        return await self.client._request("DELETE", path)
