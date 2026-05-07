#!/bin/bash

# AI Exotic Car Agent - Instant Deploy Script
# This script sets up and deploys the entire system

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   AI Exotic Car Agent - Instant Deploy                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check current directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run from project root."
    exit 1
fi

echo -e "${BLUE}📋 Deployment Options:${NC}"
echo "1. Docker (Recommended - all-in-one)"
echo "2. Local PostgreSQL setup"
echo "3. Dry-run test (no database)"
echo ""
read -p "Choose option (1-3): " DEPLOY_CHOICE

case $DEPLOY_CHOICE in
    1)
        echo -e "${BLUE}🐳 Starting Docker deployment...${NC}"

        # Check if docker is installed
        if ! command -v docker &> /dev/null; then
            echo "❌ Docker is not installed. Please install Docker first."
            exit 1
        fi

        # Check if docker-compose is available
        if ! command -v docker-compose &> /dev/null; then
            echo "⚠️  Using 'docker compose' instead of 'docker-compose'"
            DOCKER_COMPOSE="docker compose"
        else
            DOCKER_COMPOSE="docker-compose"
        fi

        cd docker
        echo -e "${YELLOW}⏳ Starting PostgreSQL and application...${NC}"
        $DOCKER_COMPOSE up -d

        echo ""
        echo -e "${GREEN}✓ Docker deployment started!${NC}"
        echo ""
        echo "Container Status:"
        $DOCKER_COMPOSE ps

        echo ""
        echo -e "${BLUE}📍 Database will be ready in 10-15 seconds${NC}"
        echo "Run this to check logs:"
        echo "  cd docker && docker-compose logs -f app"
        echo ""
        echo "To stop:"
        echo "  cd docker && docker-compose down"
        ;;

    2)
        echo -e "${BLUE}🗄️  Local PostgreSQL Setup${NC}"

        # Check if PostgreSQL is installed
        if ! command -v psql &> /dev/null; then
            echo "❌ PostgreSQL is not installed."
            echo "Please install PostgreSQL first:"
            echo "  macOS: brew install postgresql"
            echo "  Ubuntu: sudo apt-get install postgresql"
            exit 1
        fi

        # Create database
        echo -e "${YELLOW}⏳ Creating database...${NC}"
        createdb exotic_car_db 2>/dev/null || echo "⚠️  Database may already exist"

        # Import schema
        echo -e "${YELLOW}⏳ Importing schema...${NC}"
        psql -d exotic_car_db -f data/schema.sql > /dev/null 2>&1

        # Install dependencies
        echo -e "${YELLOW}⏳ Installing Python dependencies...${NC}"
        pip install -q -r requirements.txt

        echo ""
        echo -e "${GREEN}✓ Local PostgreSQL setup complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Verify database:"
        echo "   psql -d exotic_car_db -c '\\dt'"
        echo ""
        echo "2. Run scrapers:"
        echo "   python -m src.main scrape --all"
        echo ""
        echo "3. View alerts:"
        echo "   python -m src.main alerts --since 24h"
        ;;

    3)
        echo -e "${BLUE}🧪 Dry-run Test Mode${NC}"

        # Install dependencies
        echo -e "${YELLOW}⏳ Installing Python dependencies...${NC}"
        pip install -q -r requirements.txt

        echo ""
        echo -e "${YELLOW}⏳ Testing all 5 scrapers (no database)...${NC}"
        echo ""

        # Run dry-run test
        python -m src.main scrape --all --dry-run

        echo ""
        echo -e "${GREEN}✓ Dry-run test complete!${NC}"
        echo ""
        echo "If results look good, choose Option 1 or 2 to deploy with database."
        ;;

    *)
        echo "❌ Invalid option. Please choose 1, 2, or 3."
        exit 1
        ;;
esac

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Deployment Complete! 🎉                                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Documentation:"
echo "  - SETUP.md: Installation & deployment guide"
echo "  - SCRAPER_GUIDE.md: Scraper details"
echo "  - IMPLEMENTATION_STATUS.md: System status"
echo ""
echo "📞 Next steps:"
echo "  1. Monitor the system"
echo "  2. Configure webhooks (optional)"
echo "  3. Track alerts"
echo ""
