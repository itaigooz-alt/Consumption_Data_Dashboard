#!/bin/bash
# Deployment Script for Consumption Dashboard
# Based on PeerPlayGames dashboard_deployment_template

set -e

echo "=========================================="
echo "Consumption Dashboard - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "consumption_dashboard.py" ]; then
    echo -e "${RED}❌ Error: consumption_dashboard.py not found${NC}"
    echo "Please run this script from the Consumption project directory"
    exit 1
fi

echo -e "${GREEN}✅ Found consumption_dashboard.py${NC}"
echo ""

# Step 1: Verify Git repository
echo "Step 1: Checking Git repository..."
if [ -d ".git" ]; then
    echo -e "${GREEN}✅ Git repository found${NC}"
    CURRENT_BRANCH=$(git branch --show-current)
    echo "   Current branch: $CURRENT_BRANCH"
    
    # Check if there are uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
        echo "   Consider committing before deployment:"
        echo "   git add . && git commit -m 'Your message'"
        read -p "   Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✅ No uncommitted changes${NC}"
    fi
    
    # Check remote
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [ -n "$REMOTE_URL" ]; then
        echo -e "${GREEN}✅ Remote configured: $REMOTE_URL${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: No remote repository configured${NC}"
    fi
else
    echo -e "${RED}❌ Error: Not a Git repository${NC}"
    echo "Please initialize Git first: git init"
    exit 1
fi
echo ""

# Step 2: Verify required files
echo "Step 2: Checking required files..."
REQUIRED_FILES=("consumption_dashboard.py" "requirements.txt" "runtime.txt")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ Found $file${NC}"
    else
        echo -e "${RED}❌ Missing $file${NC}"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required files. Please create them before deploying.${NC}"
    exit 1
fi
echo ""

# Step 3: Check .streamlit/config.toml
echo "Step 3: Checking Streamlit configuration..."
if [ -f ".streamlit/config.toml" ]; then
    echo -e "${GREEN}✅ Found .streamlit/config.toml${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: .streamlit/config.toml not found${NC}"
    echo "   Creating default configuration..."
    mkdir -p .streamlit
    cat > .streamlit/config.toml << EOF
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[browser]
gatherUsageStats = false
EOF
    echo -e "${GREEN}✅ Created .streamlit/config.toml${NC}"
fi
echo ""

# Step 4: Verify Python dependencies
echo "Step 4: Checking Python dependencies..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"
    
    # Check if requirements.txt has content
    if [ -s "requirements.txt" ]; then
        echo -e "${GREEN}✅ requirements.txt is not empty${NC}"
        echo "   Dependencies listed:"
        while IFS= read -r line; do
            if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
                echo "   - $line"
            fi
        done < requirements.txt
    else
        echo -e "${YELLOW}⚠️  Warning: requirements.txt is empty${NC}"
    fi
else
    echo -e "${RED}❌ Error: Python3 not found${NC}"
    exit 1
fi
echo ""

# Step 5: Deployment instructions
echo "=========================================="
echo "Deployment Instructions"
echo "=========================================="
echo ""
echo "Your dashboard is ready for deployment!"
echo ""
echo "Option 1: Streamlit Cloud (Recommended)"
echo "----------------------------------------"
echo "1. Go to: https://share.streamlit.io"
echo "2. Sign in with GitHub"
echo "3. Click 'New app'"
echo "4. Select repository: itaigooz-alt/Consumption_Data_Dashboard"
echo "5. Branch: main"
echo "6. Main file: consumption_dashboard.py"
echo "7. Click 'Deploy!'"
echo ""
echo "After deployment, configure secrets in Streamlit Cloud:"
echo "- GOOGLE_APPLICATION_CREDENTIALS_JSON (service account JSON)"
echo "- GOOGLE_OAUTH_CLIENT_ID"
echo "- GOOGLE_OAUTH_CLIENT_SECRET"
echo "- STREAMLIT_REDIRECT_URI (your Streamlit Cloud URL)"
echo ""
echo "Option 2: Push to GitHub (if not already done)"
echo "-----------------------------------------------"
if [ -n "$REMOTE_URL" ]; then
    echo "Run: git push origin $CURRENT_BRANCH"
else
    echo "First, add a remote:"
    echo "  git remote add origin https://github.com/itaigooz-alt/Consumption_Data_Dashboard.git"
    echo "Then push:"
    echo "  git push -u origin $CURRENT_BRANCH"
fi
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Deployment script completed successfully!${NC}"
echo "=========================================="

