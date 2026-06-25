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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables"
        payload = {"table_name": name}
        if description:
            payload["description"] = description
        if schema:
            payload["schema_definition"] = schema

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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables"
        params = {"skip": skip, "limit": limit}
        response = await self.client._request("GET", path, params=params)
        return response.get("data", response.get("tables", []))

    async def get(self, table_name: str) -> dict[str, Any]:
        """
        Get table details.

        Args:
            table_name: Name of the table

        Returns:
            Dict with table details including schema
        """
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}"
        return await self.client._request("GET", path)

    async def delete(self, table_name: str) -> dict[str, Any]:
        """
        Delete a table.

        Args:
            table_name: Name of the table to delete

        Returns:
            Dict with deletion confirmation
        """
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}"
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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}/rows"
        # Insert rows one at a time (API expects single row_data per request)
        results = []
        for row in rows:
            result = await self.client._request("POST", path, json={"row_data": row})
            results.append(result)
        return {"inserted": len(results), "rows": results}

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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}/query"
        body: dict[str, Any] = {"skip": skip, "limit": limit}
        if filter:
            # ZeroDB stores all values as text in JSONB - convert to strings
            # and remove None values (ZeroDB can't filter IS NULL this way)
            clean_filter = {}
            for k, v in filter.items():
                if v is None:
                    continue  # Skip null filters
                elif isinstance(v, bool):
                    clean_filter[k] = v  # Booleans work as-is
                elif isinstance(v, (int, float)):
                    clean_filter[k] = str(v)  # Convert numbers to strings
                else:
                    clean_filter[k] = v
            if clean_filter:
                body["filters"] = clean_filter

        response = await self.client._request("POST", path, json=body)
        raw_rows = response.get("data", response.get("rows", []))
        # ZeroDB wraps row data inside row_data field - flatten it
        result = []
        for row in raw_rows:
            if isinstance(row, dict) and "row_data" in row:
                flat = {**row["row_data"], "_row_id": row.get("row_id"), "_created_at": row.get("created_at")}
                result.append(flat)
            else:
                result.append(row)
        return result

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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}/rows/{row_id}"
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
        path = f"/api/v1/projects/{self.client.project_id}/database/tables/{table_name}/rows/{row_id}"
        return await self.client._request("DELETE", path)
