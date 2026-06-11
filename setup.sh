#!/bin/bash

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Work Equipment SOP plugin..."

# Check for openpyxl (required for Excel output)
if ! python3 -c "import openpyxl" 2>/dev/null; then
  echo ""
  echo "  Installing openpyxl (required for Excel output)..."
  pip3 install openpyxl --quiet && echo "  openpyxl installed." || echo "  Warning: could not install openpyxl. Run: pip3 install openpyxl"
fi

# Create output directory
mkdir -p "$REPO_DIR/output"

mkdir -p ~/.claude/commands

_link() {
  local target="$1"
  local source="$2"
  local label="$3"
  if [ -L "$target" ]; then
    rm "$target"
  elif [ -e "$target" ]; then
    echo "Warning: $target already exists and is not a symlink — skipping"
    return
  fi
  ln -s "$source" "$target"
  echo "  Linked: $label"
}

_link ~/.claude/commands/we-transcribe.md  "$REPO_DIR/skills/transcribe/SKILL.md"   "we-transcribe"
_link ~/.claude/commands/we-sub-assembly.md "$REPO_DIR/skills/sub-assembly/SKILL.md" "we-sub-assembly"
_link ~/.claude/commands/we-symptoms.md    "$REPO_DIR/skills/symptoms/SKILL.md"      "we-symptoms"

echo ""
echo "Done. Skills installed:"
echo "  /we-transcribe  — process a parts manual PDF into the Wave X Parts tab"
echo "  /we-sub-assembly — build Sub-Assemblies + High-Level tabs with Repair Task IDs"
echo "  /we-symptoms     — build Symptoms tab with Symptom IDs"
echo ""
echo "Restart Claude Code for skills to appear."
