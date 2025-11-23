#!/bin/bash

###############################################################################
# SaaS OCR Platform - Quick Deployment Script
###############################################################################
#
# This script automates the complete deployment of the SaaS OCR platform.
#
# Usage:
#   ./deploy.sh [options]
#
# Options:
#   --full          Full deployment with all seed data (default)
#   --fresh         Drop existing database and deploy fresh (WARNING: destructive)
#   --schema-only   Create schema only, skip seed data
#   --help          Show this help message
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
DROP_EXISTING=false
SKIP_SEED=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fresh)
            DROP_EXISTING=true
            shift
            ;;
        --schema-only)
            SKIP_SEED=true
            shift
            ;;
        --full)
            # Default behavior, do nothing
            shift
            ;;
        --help)
            echo "SaaS OCR Platform - Quick Deployment Script"
            echo ""
            echo "Usage: ./deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --full          Full deployment with all seed data (default)"
            echo "  --fresh         Drop existing database and deploy fresh (WARNING: destructive)"
            echo "  --schema-only   Create schema only, skip seed data"
            echo "  --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║         SaaS OCR Platform - Deployment Script                 ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found!${NC}"
    echo ""
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${GREEN}✓ .env file created${NC}"
        echo ""
        echo -e "${YELLOW}Please edit .env and configure your settings before continuing.${NC}"
        echo -e "${YELLOW}Press Enter to continue after editing .env, or Ctrl+C to cancel...${NC}"
        read
    else
        echo -e "${RED}Error: .env.example not found!${NC}"
        exit 1
    fi
fi

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo -e "${RED}Error: backend directory not found!${NC}"
    echo "Please run this script from the project root directory."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed!${NC}"
    exit 1
fi

echo -e "${BLUE}Step 1: Checking PostgreSQL connection...${NC}"
# Check if PostgreSQL is running using Docker Compose
if command -v docker-compose &> /dev/null; then
    if docker-compose ps postgres | grep -q "Up"; then
        echo -e "${GREEN}✓ PostgreSQL is running (Docker)${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL container not running, starting...${NC}"
        docker-compose up -d postgres redis minio
        echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
        sleep 5
        echo -e "${GREEN}✓ PostgreSQL started${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker Compose not found, assuming PostgreSQL is running locally${NC}"
fi
echo ""

echo -e "${BLUE}Step 2: Installing Python dependencies...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate 2>/dev/null || . venv/bin/activate

# Install dependencies quietly
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo -e "${BLUE}Step 3: Running deployment script...${NC}"
echo ""

# Build command
CMD="python deploy_with_seed_data.py"

if [ "$DROP_EXISTING" = true ]; then
    CMD="$CMD --drop-existing"
fi

if [ "$SKIP_SEED" = true ]; then
    CMD="$CMD --skip-seed"
fi

# Run deployment
eval $CMD

DEPLOY_STATUS=$?

if [ $DEPLOY_STATUS -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║              ✓ Deployment Completed Successfully!             ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo ""
    echo "1. Start the application:"
    echo "   ${BLUE}docker-compose up -d${NC}"
    echo "   Or: ${BLUE}cd backend && uvicorn app.main:app --reload${NC}"
    echo ""
    echo "2. Access the API documentation:"
    echo "   ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo "3. Login credentials:"
    echo "   Email: ${BLUE}admin@saasocr.com${NC}"
    echo "   Password: ${BLUE}Password123!${NC}"
    echo ""
    echo "4. View detailed documentation:"
    echo "   ${BLUE}cat DEPLOYMENT.md${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                ║${NC}"
    echo -e "${RED}║                  ✗ Deployment Failed!                          ║${NC}"
    echo -e "${RED}║                                                                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check PostgreSQL is running: ${BLUE}docker-compose ps postgres${NC}"
    echo "2. Verify database connection in .env file"
    echo "3. Check logs above for specific error messages"
    echo "4. See DEPLOYMENT.md for detailed troubleshooting"
    echo ""
    exit 1
fi
