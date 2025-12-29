#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script for dothack-backend

This script tests all implemented API endpoints to verify they are working correctly.

Usage:
    python test_all_endpoints.py --base-url http://localhost:8000
    python test_all_endpoints.py --base-url https://your-app.railway.app

Requirements:
    pip install httpx rich python-dotenv
"""

import argparse
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint

console = Console()


class APITester:
    """Test all API endpoints"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.results: List[Dict[str, Any]] = []

    async def test_endpoint(
        self,
        method: str,
        path: str,
        name: str,
        expected_status: int = 200,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, params=params)
                elif method == "POST":
                    response = await client.post(url, json=data)
                elif method == "PUT":
                    response = await client.put(url, json=data)
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                result = {
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "expected": expected_status,
                    "passed": response.status_code == expected_status,
                    "response_time": response.elapsed.total_seconds(),
                    "error": None,
                }

                # Try to parse JSON response
                try:
                    result["response"] = response.json()
                except:
                    result["response"] = response.text[:200]

                return result

        except Exception as e:
            return {
                "name": name,
                "method": method,
                "path": path,
                "status": 0,
                "expected": expected_status,
                "passed": False,
                "response_time": 0,
                "error": str(e),
                "response": None,
            }

    async def run_all_tests(self):
        """Run all API endpoint tests"""

        console.print("\n[bold blue]🚀 Starting API Endpoint Tests[/bold blue]\n")

        # Define all test cases
        tests = [
            # Health & Docs
            ("GET", "/health", "Health Check", 200),
            ("GET", "/", "Root Endpoint", 200),
            ("GET", "/v1/docs", "API Documentation", 200),
            ("GET", "/openapi.json", "OpenAPI Schema", 200),

            # Hackathon Endpoints
            ("GET", "/api/v1/hackathons", "List Hackathons", 200),
            ("GET", "/api/v1/hackathons/test-id", "Get Hackathon (404 expected)", 404),
            ("GET", "/api/v1/hackathons/test-id/stats", "Hackathon Stats (404 expected)", 404),
            ("GET", "/api/v1/hackathons/test-id/participants", "List Participants (404 expected)", 404),

            # Search Endpoints
            (
                "POST",
                "/api/v1/search",
                "Semantic Search",
                200,
                {"query": "AI machine learning", "limit": 5},
            ),
            (
                "POST",
                "/api/v1/hackathons/test-id/search",
                "Hackathon Search (404 expected)",
                404,
                {"query": "AI", "limit": 5},
            ),

            # Recommendations Endpoints
            (
                "GET",
                "/api/v1/hackathons/test-id/recommendations/judge",
                "Judge Recommendations (404 expected)",
                404,
            ),
            (
                "POST",
                "/api/v1/hackathons/test-id/recommendations/team",
                "Team Suggestions (404 expected)",
                404,
                {"participant_ids": ["id1", "id2"]},
            ),

            # Export Endpoints
            ("GET", "/hackathons/test-id/export", "Export Hackathon (404 expected)", 404),
            ("GET", "/hackathons/test-id/rlhf/export", "Export RLHF (404 expected)", 404),
            ("GET", "/api/v1/hackathons/test-id/export", "Export Hackathon Data (404 expected)", 404),

            # File Upload Endpoints
            ("POST", "/files/teams/team-1/logo", "Upload Team Logo (422 expected)", 422),
            ("GET", "/files/teams/team-1", "List Team Files", 200),
            ("GET", "/files/test-file-id/metadata", "File Metadata (404 expected)", 404),

            # Team Endpoints
            ("GET", "/teams", "List Teams", 200),
            ("GET", "/teams/test-id", "Get Team (404 expected)", 404),

            # Submission Endpoints
            ("GET", "/v1/submissions", "List Submissions", 200),
            ("GET", "/v1/submissions/test-id", "Get Submission (404 expected)", 404),
            ("POST", "/v1/submissions/test-id/similar", "Similar Submissions (404 expected)", 404, {}),

            # Judging Endpoints
            ("GET", "/judging/assignments", "Judging Assignments (401 expected)", 401),
            ("GET", "/judging/hackathons/test-id/results", "Hackathon Results (404 expected)", 404),
        ]

        # Run tests with progress bar
        with Progress() as progress:
            task = progress.add_task("[cyan]Running tests...", total=len(tests))

            for test_args in tests:
                if len(test_args) == 4:
                    method, path, name, expected = test_args
                    result = await self.test_endpoint(method, path, name, expected)
                else:
                    method, path, name, expected, data = test_args
                    result = await self.test_endpoint(method, path, name, expected, data=data)

                self.results.append(result)
                progress.update(task, advance=1)

                # Show real-time results
                status_icon = "✅" if result["passed"] else "❌"
                console.print(
                    f"{status_icon} {result['name']}: {result['status']} "
                    f"({result['response_time']:.2f}s)"
                )

    def print_summary(self):
        """Print test results summary"""

        console.print("\n[bold green]📊 Test Results Summary[/bold green]\n")

        # Create results table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", width=8)
        table.add_column("Endpoint", width=40)
        table.add_column("Method", width=8)
        table.add_column("Expected", width=10)
        table.add_column("Got", width=10)
        table.add_column("Time", width=10)

        passed_count = 0
        failed_count = 0

        for result in self.results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            status_style = "green" if result["passed"] else "red"

            if result["passed"]:
                passed_count += 1
            else:
                failed_count += 1

            table.add_row(
                f"[{status_style}]{status}[/{status_style}]",
                result["name"],
                result["method"],
                str(result["expected"]),
                str(result["status"]),
                f"{result['response_time']:.2f}s",
            )

        console.print(table)

        # Print statistics
        total = len(self.results)
        pass_rate = (passed_count / total * 100) if total > 0 else 0

        console.print(f"\n[bold]Total Tests:[/bold] {total}")
        console.print(f"[bold green]Passed:[/bold green] {passed_count}")
        console.print(f"[bold red]Failed:[/bold red] {failed_count}")
        console.print(f"[bold blue]Pass Rate:[/bold blue] {pass_rate:.1f}%\n")

        # Print failed tests details
        if failed_count > 0:
            console.print("[bold red]❌ Failed Tests Details:[/bold red]\n")
            for result in self.results:
                if not result["passed"]:
                    console.print(f"[red]• {result['name']}[/red]")
                    console.print(f"  Method: {result['method']} {result['path']}")
                    console.print(
                        f"  Expected: {result['expected']}, Got: {result['status']}"
                    )
                    if result["error"]:
                        console.print(f"  Error: {result['error']}")
                    console.print()

    def save_results(self, filename: str = "test_results.json"):
        """Save test results to JSON file"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r["passed"]),
            "failed": sum(1 for r in self.results if not r["passed"]),
            "results": self.results,
        }

        with open(filename, "w") as f:
            json.dump(output, f, indent=2)

        console.print(f"[green]✅ Results saved to {filename}[/green]")


async def main():
    parser = argparse.ArgumentParser(description="Test all dothack-backend API endpoints")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to test_results.json",
    )

    args = parser.parse_args()

    # Create tester and run tests
    tester = APITester(args.base_url)

    console.print(f"[bold cyan]Testing API at:[/bold cyan] {args.base_url}\n")

    await tester.run_all_tests()
    tester.print_summary()

    if args.save:
        tester.save_results()


if __name__ == "__main__":
    asyncio.run(main())
