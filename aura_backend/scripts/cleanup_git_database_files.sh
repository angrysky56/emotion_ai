#!/bin/bash

# Script to remove previously committed database files from git history
# This will clean up any database files that were accidentally committed

echo "🧹 Cleaning up database files from git history..."
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}Error: Not in a git repository${NC}"
        exit 1
    fi
}

# Function to remove files from git history
remove_from_git() {
    local pattern="$1"
    local description="$2"

    echo -e "${YELLOW}Removing $description from git history...${NC}"

    # Check if any files match the pattern
    if git ls-files | grep -q "$pattern"; then
        echo -e "${BLUE}Found files matching: $pattern${NC}"
        git ls-files | grep "$pattern"

        # Remove from current index
        git rm --cached -r "$pattern" 2>/dev/null || true

        # Remove from git history (WARNING: This rewrites history)
        git filter-branch --force --index-filter \
            "git rm --cached --ignore-unmatch -r $pattern" \
            --prune-empty --tag-name-filter cat -- --all 2>/dev/null || true

        echo -e "${GREEN}✅ Removed $description from git history${NC}"
    else
        echo -e "${BLUE}No files found matching: $pattern${NC}"
    fi
}

# Main execution
check_git_repo

echo -e "${BLUE}This script will remove database files from git history.${NC}"
echo -e "${YELLOW}WARNING: This will rewrite git history!${NC}"
echo -e "${YELLOW}Make sure you have backed up your repository before proceeding.${NC}"
echo ""
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

echo -e "${BLUE}Cleaning up database and data files...${NC}"

# Remove database directories and files
remove_from_git "aura_backend/aura_chroma_db/*" "ChromaDB files"
remove_from_git "aura_backend/aura_data/users/*" "User data files"
remove_from_git "aura_backend/aura_data/sessions/*" "Session files"
remove_from_git "aura_backend/aura_data/exports/*" "Export files"
remove_from_git "aura_backend/aura_data/backups/*" "Backup files"
remove_from_git "aura_backend/memvid_data/*" "Memvid data files"
remove_from_git "aura_backend/memvid_videos/*" "Memvid video files"
remove_from_git "aura_backend/chromadb_backups/*" "ChromaDB backup files"
remove_from_git "aura_backend/auto_backups/*" "Auto backup files"
remove_from_git "*.db" "Database files"
remove_from_git "*.sqlite*" "SQLite files"

# Clean up filter-branch refs
echo -e "${BLUE}Cleaning up git references...${NC}"
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d 2>/dev/null || true
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo -e "${GREEN}🎉 Git cleanup complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "${BLUE}1. Add and commit the new .gitkeep files${NC}"
echo -e "${BLUE}2. Force push to update remote repository: git push --force-with-lease${NC}"
echo -e "${YELLOW}3. All team members should re-clone the repository${NC}"
echo ""
echo -e "${GREEN}Your local data directories are preserved with .gitkeep files!${NC}"
