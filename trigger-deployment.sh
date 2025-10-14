#!/bin/bash

# Trigger GitHub Actions Workflow ohne Push
# Verwendet GitHub CLI (gh) für manuelles Workflow-Triggering

set -e

echo "🚀 Trigger Online Deployment (without Push)"
echo "================================================"
echo ""

# Prüfe ob GitHub CLI installiert ist
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed!"
    echo ""
    echo "Install with:"
    echo "  # Ubuntu/Debian:"
    echo "  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    echo "  echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
    echo "  sudo apt update && sudo apt install gh"
    echo ""
    echo "  # macOS:"
    echo "  brew install gh"
    echo ""
    echo "  # Or download from: https://cli.github.com/"
    echo ""
    echo "Then authenticate with: gh auth login"
    echo ""
    exit 1
fi

# Prüfe ob authentifiziert
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub!"
    echo "Run: gh auth login"
    exit 1
fi

BRANCH=$(git branch --show-current)

echo "Current branch: $BRANCH"
echo ""

# Prüfe ob Änderungen committed sind
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes!"
    echo ""
    git status -s
    echo ""
    read -p "Commit changes first? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        read -p "Commit message: " msg
        git add -A
        git commit -m "$msg"
        echo "✅ Changes committed"
    fi
fi

echo ""
echo "Deployment Options:"
echo "  1) Deploy current branch ($BRANCH) online"
echo "  2) Trigger specific workflow"
echo "  3) View workflow runs"
echo "  4) Cancel running workflows"
echo ""

read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Triggering deployment for: $BRANCH"
        echo ""
        
        # Push ohne zu mergen (force push zum Remote)
        echo "Pushing branch to GitHub..."
        git push origin $BRANCH
        
        echo ""
        echo "✅ Branch pushed! GitHub Actions will start automatically."
        echo ""
        echo "View progress:"
        gh run watch
        ;;
    2)
        echo ""
        echo "Available workflows:"
        gh workflow list
        echo ""
        read -p "Enter workflow name or ID: " workflow
        
        echo ""
        echo "Triggering workflow: $workflow"
        gh workflow run "$workflow" --ref $BRANCH
        
        echo ""
        echo "✅ Workflow triggered!"
        echo "View progress:"
        gh run watch
        ;;
    3)
        echo ""
        echo "Recent workflow runs:"
        gh run list --limit 10
        echo ""
        read -p "Watch a specific run? (run ID or press Enter to skip): " run_id
        if [ -n "$run_id" ]; then
            gh run watch $run_id
        fi
        ;;
    4)
        echo ""
        echo "Running workflows:"
        gh run list --status in_progress --limit 10
        echo ""
        read -p "Enter run ID to cancel: " run_id
        if [ -n "$run_id" ]; then
            gh run cancel $run_id
            echo "✅ Workflow cancelled"
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "View all runs: gh run list"
echo "View workflow details: gh workflow view"
echo "View logs: gh run view <run-id>"
echo "================================================"
