#!/bin/bash

# Trigger GitHub Actions Workflow manuell ohne Commit/Push
# Verwendet workflow_dispatch Event

set -e

BRANCH=$(git branch --show-current)

echo "🚀 Manual GitHub Actions Trigger (no commit required)"
echo "================================================"
echo "Branch: $BRANCH"
echo ""

# Prüfe ob gh authenticated ist
if ! gh auth status &> /dev/null 2>&1; then
    echo "❌ Not authenticated with GitHub!"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Zeige verfügbare Workflows
echo "📋 Available workflows:"
gh workflow list

echo ""
echo "Options:"
echo "  1) Trigger deploy workflow for current branch"
echo "  2) View workflow runs"
echo "  3) Watch latest run"
echo ""

read -p "Choose option [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Triggering deployment workflow..."
        echo "Branch: $BRANCH"
        
        # Trigger workflow mit workflow_dispatch
        gh workflow run deploy.yml --ref $BRANCH || {
            echo ""
            echo "⚠️  Direct trigger failed. Trying alternative method..."
            echo ""
            echo "Creating empty commit to trigger workflow..."
            git commit --allow-empty -m "Trigger deployment for $BRANCH"
            git push origin $BRANCH
            echo "✅ Pushed empty commit"
        }
        
        echo ""
        echo "✅ Workflow triggered!"
        echo ""
        sleep 2
        echo "Watching workflow progress..."
        gh run watch
        ;;
    2)
        echo ""
        gh run list --limit 20
        ;;
    3)
        echo ""
        echo "Watching latest run..."
        gh run watch
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "View all runs: https://github.com/sebastianuzk/uzk-masterarbeit/actions"
echo "================================================"
