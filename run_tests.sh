#!/bin/bash

# Test Runner Script for SaaS OCR Project
# Runs comprehensive test suite with detailed reporting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SaaS OCR - Comprehensive Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d "env" ]; then
    echo -e "${YELLOW}Warning: No virtual environment found${NC}"
    echo -e "${YELLOW}Consider creating one: python -m venv venv${NC}"
    echo ""
fi

# Create test reports directory
mkdir -p test-reports

# Function to run tests
run_test_suite() {
    local suite_name=$1
    local marker=$2
    local test_path=$3

    echo -e "${BLUE}Running ${suite_name}...${NC}"

    if pytest ${test_path} -v -m ${marker} \
        --html=test-reports/${suite_name}-report.html \
        --self-contained-html \
        --json-report-file=test-reports/${suite_name}-report.json \
        2>&1 | tee test-reports/${suite_name}-output.txt; then
        echo -e "${GREEN}✅ ${suite_name} PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ ${suite_name} FAILED${NC}"
        return 1
    fi
}

# Parse command line arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "unit")
        echo -e "${BLUE}Running Unit Tests Only${NC}"
        run_test_suite "unit-tests" "unit" "tests/unit"
        ;;

    "integration")
        echo -e "${BLUE}Running Integration Tests Only${NC}"
        run_test_suite "integration-tests" "integration" "tests/integration"
        ;;

    "e2e")
        echo -e "${BLUE}Running E2E Tests Only${NC}"
        run_test_suite "e2e-tests" "e2e" "tests/e2e"
        ;;

    "all")
        echo -e "${BLUE}Running All Test Suites${NC}"
        echo ""

        # Track failures
        FAILED=0

        # Run unit tests
        if ! run_test_suite "unit-tests" "unit" "tests/unit"; then
            FAILED=$((FAILED + 1))
        fi
        echo ""

        # Run integration tests
        if ! run_test_suite "integration-tests" "integration" "tests/integration"; then
            FAILED=$((FAILED + 1))
        fi
        echo ""

        # Run E2E tests
        if ! run_test_suite "e2e-tests" "e2e" "tests/e2e"; then
            FAILED=$((FAILED + 1))
        fi
        echo ""

        # Generate coverage report
        echo -e "${BLUE}Generating coverage report...${NC}"
        pytest tests/ --cov=backend/app \
            --cov-report=html:test-reports/coverage-html \
            --cov-report=xml:test-reports/coverage.xml \
            --cov-report=term-missing \
            > test-reports/coverage-output.txt 2>&1

        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}Test Summary${NC}"
        echo -e "${BLUE}========================================${NC}"

        if [ $FAILED -eq 0 ]; then
            echo -e "${GREEN}✅ All test suites passed!${NC}"
            echo -e "${GREEN}Reports available in: test-reports/${NC}"
            exit 0
        else
            echo -e "${RED}❌ ${FAILED} test suite(s) failed${NC}"
            echo -e "${YELLOW}Check reports in: test-reports/${NC}"
            exit 1
        fi
        ;;

    "quick")
        echo -e "${BLUE}Running Quick Smoke Tests${NC}"
        pytest tests/ -v -m smoke --maxfail=3
        ;;

    "coverage")
        echo -e "${BLUE}Running Tests with Coverage Analysis${NC}"
        pytest tests/ -v \
            --cov=backend/app \
            --cov-report=html:test-reports/coverage-html \
            --cov-report=term-missing \
            --cov-report=xml:test-reports/coverage.xml
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [unit|integration|e2e|all|quick|coverage]"
        echo ""
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  e2e         - Run end-to-end tests only"
        echo "  all         - Run all test suites (default)"
        echo "  quick       - Run quick smoke tests"
        echo "  coverage    - Run with coverage analysis"
        exit 1
        ;;
esac
