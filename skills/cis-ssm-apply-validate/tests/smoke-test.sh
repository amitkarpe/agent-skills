#!/usr/bin/env bash
set -euo pipefail

# Smoke test for SSM apply workflow

echo "=== SSM Apply Workflow Smoke Test ==="
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR/fixtures"
SMOKE_OUT="/tmp/ssm-smoke-test-$(date +%s)"

echo "Test output: $SMOKE_OUT"
echo

# Test 1: Validate script works
echo "1. Testing validate.sh..."
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir "$SMOKE_OUT/validate" 2>&1 | grep -q "Validation passed"; then
  echo "   ✓ Validation works"
else
  echo "   ✗ Validation failed"
  exit 1
fi

# Test 2: Check evidence files created
echo "2. Checking evidence files..."
EXPECTED_FILES=(
  "$SMOKE_OUT/validate/validate.log"
  "$SMOKE_OUT/validate/validate-errors.log"
)

for file in "${EXPECTED_FILES[@]}"; do
  if [[ -f "$file" ]]; then
    echo "   ✓ $(basename "$file")"
  else
    echo "   ✗ Missing: $(basename "$file")"
    exit 1
  fi
done

# Test 3: Parameter validation catches bad schema
echo "3. Testing parameter schema validation..."
echo '{"bad": 123}' > /tmp/smoke-bad-params.json
rm -rf "$SMOKE_OUT/bad-params"
if ! "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file /tmp/smoke-bad-params.json \
  --output-dir "$SMOKE_OUT/bad-params" 2>&1; then
  echo "   ✓ Rejects invalid parameter types"
else
  echo "   ✗ Should reject invalid parameter types"
  exit 1
fi
rm -f /tmp/smoke-bad-params.json

# Test 4: Output directory isolation
echo "4. Testing output directory isolation..."
rm -rf "$SMOKE_OUT/nonempty"
mkdir -p "$SMOKE_OUT/nonempty"
touch "$SMOKE_OUT/nonempty/existing"
if ! "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir "$SMOKE_OUT/nonempty" 2>&1; then
  echo "   ✓ Rejects non-empty output directory"
else
  echo "   ✗ Should reject non-empty directory"
  exit 1
fi

# Test 5: Dry-run mode
echo "5. Testing dry-run mode..."
rm -rf "$SMOKE_OUT/dryrun"
if "$ROOT_DIR/scripts/apply.sh" \
  --document-name SmokeTest \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --instance-id i-fakefakefake \
  --output-dir "$SMOKE_OUT/dryrun" \
  --dry-run 2>&1 | grep -q "DRY-RUN"; then
  echo "   ✓ Dry-run mode works"
else
  echo "   ✗ Dry-run mode failed"
  exit 1
fi

echo
echo "=== All smoke tests passed ==="
echo "Evidence preserved in: $SMOKE_OUT"
