#!/usr/bin/env bash
# Assemble the Hugging Face Space staging directory from the backend sources.
# Run from the repository root:  bash deploy/hf-space/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAGING="$ROOT/deploy/hf-space/staging"

rm -rf "$STAGING"
mkdir -p "$STAGING"

cp "$ROOT/deploy/hf-space/README.md" "$STAGING/"
cp "$ROOT/deploy/hf-space/Dockerfile" "$STAGING/"
cp "$ROOT/backend/requirements.txt" "$STAGING/"
cp -r "$ROOT/backend/app" "$STAGING/app"
find "$STAGING" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "Staging ready: $STAGING"
echo "Push with:  hf upload <user>/khetse-api \"$STAGING\" . --repo-type space"
