"""
Test Runner Utility

Runs tests with comprehensive reporting and analysis.
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import os


class TestRunner:
    """Comprehensive test runner with reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "test-reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run_unit_tests(self) -> Dict:
        """Run all unit tests."""
        print("\n" + "=" * 80)
        print("RUNNING UNIT TESTS")
        print("=" * 80 + "\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/unit",
                "-v",
                "-m", "unit",
                f"--html={self.reports_dir}/unit-tests-{self.timestamp}.html",
                "--self-contained-html",
                f"--json-report-file={self.reports_dir}/unit-tests-{self.timestamp}.json",
                "--cov=backend/app",
                f"--cov-report=html:{self.reports_dir}/coverage-unit-{self.timestamp}",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return {
            "name": "Unit Tests",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def run_integration_tests(self) -> Dict:
        """Run all integration tests."""
        print("\n" + "=" * 80)
        print("RUNNING INTEGRATION TESTS")
        print("=" * 80 + "\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/integration",
                "-v",
                "-m", "integration",
                f"--html={self.reports_dir}/integration-tests-{self.timestamp}.html",
                "--self-contained-html",
                f"--json-report-file={self.reports_dir}/integration-tests-{self.timestamp}.json",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return {
            "name": "Integration Tests",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def run_e2e_tests(self) -> Dict:
        """Run all E2E tests."""
        print("\n" + "=" * 80)
        print("RUNNING E2E TESTS")
        print("=" * 80 + "\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/e2e",
                "-v",
                "-m", "e2e",
                f"--html={self.reports_dir}/e2e-tests-{self.timestamp}.html",
                "--self-contained-html",
                f"--json-report-file={self.reports_dir}/e2e-tests-{self.timestamp}.json",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return {
            "name": "E2E Tests",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def run_all_tests(self) -> Dict:
        """Run all tests together."""
        print("\n" + "=" * 80)
        print("RUNNING ALL TESTS")
        print("=" * 80 + "\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/",
                "-v",
                f"--html={self.reports_dir}/all-tests-{self.timestamp}.html",
                "--self-contained-html",
                f"--json-report-file={self.reports_dir}/all-tests-{self.timestamp}.json",
                "--cov=backend/app",
                f"--cov-report=html:{self.reports_dir}/coverage-all-{self.timestamp}",
                f"--cov-report=xml:{self.reports_dir}/coverage-{self.timestamp}.xml",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return {
            "name": "All Tests",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def generate_summary_report(self, results: List[Dict]):
        """Generate a comprehensive summary report."""
        summary_path = self.reports_dir / f"test-summary-{self.timestamp}.txt"

        with open(summary_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("TEST EXECUTION SUMMARY\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            total_passed = 0
            total_failed = 0

            for result in results:
                f.write(f"\n{result['name']}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Exit Code: {result['returncode']}\n")

                if result['returncode'] == 0:
                    f.write("Status: ✅ PASSED\n")
                    total_passed += 1
                else:
                    f.write("Status: ❌ FAILED\n")
                    total_failed += 1

                # Parse JSON report if available
                json_report = self._find_json_report(result['name'])
                if json_report:
                    f.write(f"\nTest Statistics:\n")
                    f.write(f"  Total: {json_report.get('summary', {}).get('total', 'N/A')}\n")
                    f.write(f"  Passed: {json_report.get('summary', {}).get('passed', 'N/A')}\n")
                    f.write(f"  Failed: {json_report.get('summary', {}).get('failed', 'N/A')}\n")
                    f.write(f"  Skipped: {json_report.get('summary', {}).get('skipped', 'N/A')}\n")

                f.write("\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("OVERALL SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Test Suites Passed: {total_passed}\n")
            f.write(f"Total Test Suites Failed: {total_failed}\n")

            if total_failed == 0:
                f.write("\n✅ ALL TEST SUITES PASSED!\n")
            else:
                f.write(f"\n❌ {total_failed} TEST SUITE(S) FAILED\n")

        print(f"\n📊 Summary report generated: {summary_path}")
        return summary_path

    def _find_json_report(self, test_name: str) -> Dict:
        """Find and load JSON report for a test suite."""
        # Convert test name to filename pattern
        pattern = test_name.lower().replace(" ", "-")

        for report_file in self.reports_dir.glob(f"*{pattern}*.json"):
            if self.timestamp in str(report_file):
                try:
                    with open(report_file) as f:
                        return json.load(f)
                except Exception:
                    pass

        return {}

    def display_results(self, results: List[Dict]):
        """Display test results in console."""
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80 + "\n")

        for result in results:
            status = "✅ PASSED" if result['returncode'] == 0 else "❌ FAILED"
            print(f"{result['name']}: {status}")

        print("\n" + "=" * 80)
        total_passed = sum(1 for r in results if r['returncode'] == 0)
        total_failed = len(results) - total_passed

        print(f"Total: {len(results)} | Passed: {total_passed} | Failed: {total_failed}")
        print("=" * 80 + "\n")


def main():
    """Main entry point for test runner."""
    project_root = Path(__file__).parent.parent.parent

    runner = TestRunner(project_root)

    # Run test suites
    results = []

    # Parse command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1]

        if test_type == "unit":
            results.append(runner.run_unit_tests())
        elif test_type == "integration":
            results.append(runner.run_integration_tests())
        elif test_type == "e2e":
            results.append(runner.run_e2e_tests())
        elif test_type == "all":
            results.append(runner.run_all_tests())
        else:
            print(f"Unknown test type: {test_type}")
            print("Usage: python test_runner.py [unit|integration|e2e|all|comprehensive]")
            sys.exit(1)
    else:
        # Run comprehensive suite
        results.append(runner.run_unit_tests())
        results.append(runner.run_integration_tests())
        results.append(runner.run_e2e_tests())

    # Display and save results
    runner.display_results(results)
    summary_path = runner.generate_summary_report(results)

    # Exit with error if any tests failed
    if any(r['returncode'] != 0 for r in results):
        print("\n❌ Some tests failed. Check reports for details.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
