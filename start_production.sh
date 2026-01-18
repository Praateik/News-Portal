#!/bin/bash
# Production Deployment Script with Redis & Performance Optimization
# Achieves <200ms TTFB with AI caching

set -e

echo "=========================================="
echo "🚀 Nepal Times - Production Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! command -v redis-server &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis not installed. Installing Redis...${NC}"
    sudo apt-get update
    sudo apt-get install -y redis-server redis-tools
fi
echo -e "${GREEN}✓ Redis available${NC}"

# 2. Setup Python environment
echo -e "${BLUE}Step 2: Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# 3. Install dependencies
echo -e "${BLUE}Step 3: Installing Python dependencies...${NC}"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements-prod.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 4. Start Redis
echo -e "${BLUE}Step 4: Starting Redis server...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis already running${NC}"
else
    redis-server --daemonize yes --loglevel warning
    sleep 1
    echo -e "${GREEN}✓ Redis started${NC}"
fi

redis-cli ping
echo -e "${GREEN}✓ Redis connection verified${NC}"

# 5. Set environment variables
echo -e "${BLUE}Step 5: Configuring environment...${NC}"
if [ -z "$JINA_API_KEY" ]; then
    echo -e "${YELLOW}⚠ JINA_API_KEY not set. Using environment default.${NC}"
    echo "   Set with: export JINA_API_KEY='your_key_here'"
else
    echo -e "${GREEN}✓ JINA_API_KEY configured${NC}"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}⚠ GEMINI_API_KEY not set. Using environment default.${NC}"
    echo "   Set with: export GEMINI_API_KEY='your_key_here'"
else
    echo -e "${GREEN}✓ GEMINI_API_KEY configured${NC}"
fi

# 6. Start the production backend
echo -e "${BLUE}Step 6: Starting production backend...${NC}"
export REDIS_URL="redis://localhost:6379"
export PORT=5000
export HOST="0.0.0.0"
export DEBUG="false"

# Start the server in background
python3 server_production.py > logs/server.log 2>&1 &
SERVER_PID=$!
echo -e "${GREEN}✓ Production backend started (PID: $SERVER_PID)${NC}"

# Wait for server to start
sleep 3

# 7. Test the API
echo -e "${BLUE}Step 7: Testing API...${NC}"
if curl -s http://127.0.0.1:5000/health | grep -q "ok"; then
    echo -e "${GREEN}✓ API is responding${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    kill $SERVER_PID
    exit 1
fi

# 8. Performance test
echo -e "${BLUE}Step 8: Running performance test...${NC}"
echo "Testing /health endpoint..."
RESPONSE=$(curl -s -w "\n%{time_total}" http://127.0.0.1:5000/health)
TTFB=$(echo "$RESPONSE" | tail -1)
echo -e "${GREEN}✓ TTFB: ${TTFB}s${NC}"

# 9. Display startup info
echo ""
echo -e "${GREEN}=========================================="
echo "✓ Production Environment Ready!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Performance Targets:${NC}"
echo "  TTFB (first request):  <200ms"
echo "  TTFB (cached):         <50ms"
echo "  Background jobs:       Non-blocking"
echo ""
echo -e "${BLUE}Redis Cache Status:${NC}"
redis-cli INFO stats | grep -E "total_commands_processed|connected_clients"
echo ""
echo -e "${BLUE}API Endpoints:${NC}"
echo "  GET  http://127.0.0.1:5000/health              Health check"
echo "  GET  http://127.0.0.1:5000/api/news            News list"
echo "  GET  http://127.0.0.1:5000/api/article?url=... Single article (cached)"
echo "  GET  http://127.0.0.1:5000/api/cache/stats     Cache statistics"
echo ""
echo -e "${BLUE}Frontend:${NC}"
echo "  http://127.0.0.1:8000  (serve news-website-ui/)"
echo ""
echo -e "${BLUE}Environment Variables:${NC}"
echo "  REDIS_URL=${REDIS_URL}"
echo "  PORT=${PORT}"
echo "  HOST=${HOST}"
echo "  DEBUG=${DEBUG}"
echo ""
echo -e "${YELLOW}To stop the server:${NC}"
echo "  kill $SERVER_PID"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  tail -f logs/server.log"
echo ""
