#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR/fixtures"
RUN_DIR="${HOME}/.AGENTS-temp/agent-skills/cis-ssm-apply-validate/unit-$(date +%Y%m%d-%H%M%S)"
FAILED=0

mkdir -p "$RUN_DIR"

pass() { echo "✓ $1"; }
fail() { echo "✗ $1"; FAILED=$((FAILED + 1)); }

# Test 1: validate.sh rejects missing document file
echo "Test: Missing document file"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file /nonexistent \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir "$RUN_DIR/test-out" 2>/dev/null; then
  fail "Should reject missing document"
else
  pass "Rejects missing document"
fi

# Test 2: validate.sh rejects invalid JSON
echo "Test: Invalid JSON parameters"
echo "not json" > "$RUN_DIR/bad.json"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$RUN_DIR/bad.json" \
  --output-dir "$RUN_DIR/test-out" 2>/dev/null; then
  fail "Should reject invalid JSON"
else
  pass "Rejects invalid JSON"
fi
rm "$RUN_DIR/bad.json"

# Test 3: validate.sh accepts valid inputs
echo "Test: Valid inputs"
rm -rf "$RUN_DIR/test-out"
mkdir -p "$RUN_DIR/test-out"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir "$RUN_DIR/test-out" 2>/dev/null; then
  pass "Accepts valid inputs"
else
  fail "Should accept valid inputs"
fi

# Test 4: apply.sh validates required flags
echo "Test: Missing required flags"
if "$ROOT_DIR/scripts/apply.sh" \
  --document-name TestDoc \
  --document-file "$TEST_DIR/test-doc.yaml" \
  2>/dev/null; then
  fail "Should reject missing flags"
else
  pass "Rejects missing flags"
fi

# Test 5: validate.sh rejects non-empty output directory
echo "Test: Non-empty output directory"
rm -rf "$RUN_DIR/test-out-nonempty"
mkdir -p "$RUN_DIR/test-out-nonempty"
touch "$RUN_DIR/test-out-nonempty/existing-file"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir "$RUN_DIR/test-out-nonempty" 2>/dev/null; then
  fail "Should reject non-empty output directory"
else
  pass "Rejects non-empty output directory"
fi
rm -rf "$RUN_DIR/test-out-nonempty"

# Test 6: validate.sh rejects invalid parameter schema
echo "Test: Invalid parameter schema (non-object)"
echo '["not", "an", "object"]' > "$RUN_DIR/bad-params.json"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$RUN_DIR/bad-params.json" \
  --output-dir "$RUN_DIR/test-schema" 2>/dev/null; then
  fail "Should reject non-object parameters"
else
  pass "Rejects non-object parameters"
fi
rm -f "$RUN_DIR/bad-params.json"
rm -rf "$RUN_DIR/test-schema"

# Test 7: validate.sh rejects invalid parameter value types
echo "Test: Invalid parameter value types"
echo '{"key": 123}' > "$RUN_DIR/bad-value.json"
rm -rf "$RUN_DIR/test-value"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$RUN_DIR/bad-value.json" \
  --output-dir "$RUN_DIR/test-value" 2>/dev/null; then
  fail "Should reject non-string/array parameter values"
else
  pass "Rejects invalid parameter value types"
fi
rm -f "$RUN_DIR/bad-value.json"
rm -rf "$RUN_DIR/test-value"

rm -rf "$RUN_DIR/test-out"

[[ $FAILED -eq 0 ]] && echo "All tests passed" || echo "$FAILED test(s) failed"
exit $FAILED
