#!/bin/bash

# Einfacher Deployment-Trigger via Git Push
# Committed alle Änderungen und pusht zum Branch

set -e

BRANCH=$(git branch --show-current)

echo "🚀 Deploy to GitHub (Branch: $BRANCH)"
echo "================================================"
echo ""

# Zeige Status
echo "Current changes:"
git status -s

if [[ -z $(git status -s) ]]; then
    echo "✅ No changes to commit"
    echo ""
    read -p "Push anyway to trigger deployment? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        exit 0
    fi
else
    echo ""
    read -p "Commit message: " msg
    
    if [ -z "$msg" ]; then
        msg="Deploy: Update $(date '+%Y-%m-%d %H:%M')"
    fi
    
    echo ""
    echo "Committing changes..."
    git add -A
    git commit -m "$msg"
    echo "✅ Changes committed"
fi

echo ""
echo "Pushing to GitHub..."
git push origin $BRANCH

echo ""
echo "================================================"
echo "✅ Successfully pushed to: origin/$BRANCH"
echo "================================================"
echo ""
echo "🔄 GitHub Actions will start automatically!"
echo ""
echo "View progress at:"
echo "  https://github.com/sebastianuzk/uzk-masterarbeit/actions"
echo ""
echo "Your deployment will be available at:"
if [ "$BRANCH" = "main" ]; then
    echo "  Production: http://your-domain.com:8501"
else
    SANITIZED=$(echo "$BRANCH" | sed 's/\//-/g')
    PORT=$((8500 + $(echo -n "$SANITIZED" | md5sum | cut -c1-4 | xargs printf "%d" 0x) % 100))
    echo "  Feature: http://your-domain.com:$PORT"
    echo "  (Local preview port: $PORT)"
fi
echo ""
