#!/bin/bash
# DevDebug AI - Automated GitHub Push Script
# This script will help you create and push to GitHub in one go

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         DevDebug AI - GitHub Push Automation                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Get GitHub username
echo -e "${YELLOW}Step 1: GitHub Username${NC}"
read -p "Enter your GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}Error: GitHub username is required${NC}"
    exit 1
fi

REPO_NAME="devdebug-ai"
REPO_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo -e "\n${GREEN}Repository will be created at:${NC}"
echo -e "${BLUE}${REPO_URL}${NC}\n"

# Check if git is initialized
if [ ! -d .git ]; then
    echo -e "${RED}Error: Not a git repository. Run from project root.${NC}"
    exit 1
fi

# Check if remote already exists
if git remote get-url origin &> /dev/null; then
    echo -e "${YELLOW}⚠ Remote 'origin' already exists${NC}"
    CURRENT_REMOTE=$(git remote get-url origin)
    echo -e "Current remote: ${CURRENT_REMOTE}"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        echo -e "${GREEN}✓ Removed old remote${NC}"
    else
        echo -e "${YELLOW}Keeping existing remote${NC}"
    fi
fi

# Add remote if it doesn't exist
if ! git remote get-url origin &> /dev/null; then
    echo -e "\n${YELLOW}Step 2: Adding GitHub remote...${NC}"
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✓ Remote added${NC}"
fi

# Rename branch to main
echo -e "\n${YELLOW}Step 3: Preparing branch...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    git branch -M main
    echo -e "${GREEN}✓ Branch renamed to 'main'${NC}"
else
    echo -e "${GREEN}✓ Already on 'main' branch${NC}"
fi

# Show what will be pushed
echo -e "\n${YELLOW}Step 4: Repository Status${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Files to push: $(git ls-files | wc -l)"
echo -e "Commits: $(git rev-list --count HEAD)"
echo -e "Latest commit: $(git log -1 --oneline)"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Instructions for GitHub
echo -e "${YELLOW}Step 5: Create GitHub Repository${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Before pushing, you need to create the repository on GitHub:"
echo -e ""
echo -e "  1. Go to: ${GREEN}https://github.com/new${NC}"
echo -e "  2. Repository name: ${GREEN}${REPO_NAME}${NC}"
echo -e "  3. Description: ${GREEN}AI-powered Kubernetes troubleshooting system${NC}"
echo -e "  4. Choose: Public or Private"
echo -e "  5. ${RED}IMPORTANT: Do NOT initialize with README${NC}"
echo -e "  6. Click '${GREEN}Create repository${NC}'"
echo -e ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

read -p "Have you created the repository on GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Please create the repository first, then run this script again.${NC}"
    exit 0
fi

# Push to GitHub
echo -e "\n${YELLOW}Step 6: Pushing to GitHub...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if git push -u origin main; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║              🎉 SUCCESS! Repository Pushed! 🎉            ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}Your repository is now live at:${NC}"
    echo -e "${GREEN}https://github.com/${GITHUB_USERNAME}/${REPO_NAME}${NC}\n"
    
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Visit your repository"
    echo -e "  2. Add topics/tags (kubernetes, ai, llm, rag, python)"
    echo -e "  3. Update repository description"
    echo -e "  4. Share with your team! 🚀\n"
    
    # Try to open in browser (optional)
    read -p "Would you like to open the repository in your browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}" 2>/dev/null
        elif command -v open &> /dev/null; then
            open "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
        else
            echo -e "${YELLOW}Please open manually:${NC} https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
        fi
    fi
else
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                           ║${NC}"
    echo -e "${RED}║                  ⚠ Push Failed                            ║${NC}"
    echo -e "${RED}║                                                           ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "  1. Repository doesn't exist on GitHub yet"
    echo -e "  2. Authentication failed (check credentials)"
    echo -e "  3. Repository already exists and has different content\n"
    
    echo -e "${YELLOW}Try:${NC}"
    echo -e "  • Make sure you created the repository on GitHub"
    echo -e "  • Verify your GitHub username: ${GITHUB_USERNAME}"
    echo -e "  • Check your Git credentials (git credential-manager)\n"
    
    exit 1
fi
