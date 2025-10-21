#!/bin/bash

# Railway Deployment Setup Script
# Helps prepare CalBot for Railway deployment

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║           🚂 CalBot Railway Deployment Setup 🚂                ║"
echo "║                                                                ║"
echo "╔════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}⚠️  Railway CLI not found${NC}"
    echo "Installing Railway CLI..."
    npm install -g @railway/cli
    echo -e "${GREEN}✅ Railway CLI installed${NC}"
else
    echo -e "${GREEN}✅ Railway CLI already installed${NC}"
fi
echo ""

# Check if logged in to Railway
echo "Checking Railway authentication..."
if railway whoami &> /dev/null; then
    RAILWAY_USER=$(railway whoami)
    echo -e "${GREEN}✅ Logged in to Railway as: ${RAILWAY_USER}${NC}"
else
    echo -e "${YELLOW}⚠️  Not logged in to Railway${NC}"
    echo "Please login to Railway..."
    railway login
    echo -e "${GREEN}✅ Logged in successfully${NC}"
fi
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from template..."
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}Please edit .env with your credentials${NC}"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi
echo ""

# Check environment variables
echo "Checking required environment variables in .env..."
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_KEY"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "SECRET_KEY"
    "ANTHROPIC_API_KEY"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" .env 2>/dev/null || grep -q "^${VAR}=$" .env 2>/dev/null || grep -q "^${VAR}=your_" .env 2>/dev/null; then
        MISSING_VARS+=("$VAR")
        echo -e "  ${RED}❌ ${VAR} not set${NC}"
    else
        echo -e "  ${GREEN}✅ ${VAR} is set${NC}"
    fi
done
echo ""

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}⚠️  Missing or incomplete environment variables:${NC}"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "   - $VAR"
    done
    echo ""
    echo "Please edit .env and fill in all required variables"
    echo "Then run this script again"
    exit 1
fi

# Generate SECRET_KEY if needed
if grep -q "SECRET_KEY=your-secret-key" .env 2>/dev/null; then
    echo -e "${YELLOW}Generating SECRET_KEY...${NC}"
    SECRET=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET/" .env
    else
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET/" .env
    fi
    echo -e "${GREEN}✅ Generated new SECRET_KEY${NC}"
fi
echo ""

# Check if Railway project exists
echo "Checking Railway project..."
if railway status &> /dev/null; then
    PROJECT=$(railway status | grep "Project:" | cut -d':' -f2 | xargs)
    echo -e "${GREEN}✅ Connected to Railway project: ${PROJECT}${NC}"
else
    echo -e "${YELLOW}⚠️  Not linked to a Railway project${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create a new project on Railway: https://railway.app/new"
    echo "2. Run: railway link"
    echo "3. Or run: railway init (to create a new project)"
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Railway Setup Complete!${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Create Railway Project:"
echo "   → Go to https://railway.app/new"
echo "   → Click 'Deploy from GitHub repo'"
echo "   → Select your calbot repository"
echo ""
echo "2. Create Two Services:"
echo "   → Backend service (root: /backend)"
echo "   → Frontend service (root: /frontend)"
echo ""
echo "3. Set Environment Variables:"
echo "   → Use the values from your .env file"
echo "   → See .railway-env-template.txt for reference"
echo "   → Update URLs with your Railway URLs"
echo ""
echo "4. Update Google OAuth:"
echo "   → Add Railway callback URL to Google Console"
echo "   → Format: https://YOUR-BACKEND-URL/auth/google/callback"
echo ""
echo "5. Deploy!"
echo "   → Railway deploys automatically from GitHub"
echo "   → Or run: railway up"
echo ""
echo "📚 Documentation:"
echo "   → Full guide: RAILWAY_DEPLOYMENT.md"
echo "   → Railway docs: https://docs.railway.app"
echo ""
echo "🚀 Ready to deploy to Railway!"
echo ""
