#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR/fixtures"
FAILED=0

pass() { echo "✓ $1"; }
fail() { echo "✗ $1"; FAILED=$((FAILED + 1)); }

# Test 1: validate.sh rejects missing document file
echo "Test: Missing document file"
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file /nonexistent \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir /tmp/test-out 2>/dev/null; then
  fail "Should reject missing document"
else
  pass "Rejects missing document"
fi

# Test 2: validate.sh rejects invalid JSON
echo "Test: Invalid JSON parameters"
echo "not json" > /tmp/bad.json
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file /tmp/bad.json \
  --output-dir /tmp/test-out 2>/dev/null; then
  fail "Should reject invalid JSON"
else
  pass "Rejects invalid JSON"
fi
rm /tmp/bad.json

# Test 3: validate.sh accepts valid inputs
echo "Test: Valid inputs"
rm -rf /tmp/test-out
mkdir -p /tmp/test-out
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir /tmp/test-out 2>/dev/null; then
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
rm -rf /tmp/test-out-nonempty
mkdir -p /tmp/test-out-nonempty
touch /tmp/test-out-nonempty/existing-file
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file "$TEST_DIR/params.json" \
  --output-dir /tmp/test-out-nonempty 2>/dev/null; then
  fail "Should reject non-empty output directory"
else
  pass "Rejects non-empty output directory"
fi
rm -rf /tmp/test-out-nonempty

# Test 6: validate.sh rejects invalid parameter schema
echo "Test: Invalid parameter schema (non-object)"
echo '["not", "an", "object"]' > /tmp/bad-params.json
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file /tmp/bad-params.json \
  --output-dir /tmp/test-schema 2>/dev/null; then
  fail "Should reject non-object parameters"
else
  pass "Rejects non-object parameters"
fi
rm -f /tmp/bad-params.json
rm -rf /tmp/test-schema

# Test 7: validate.sh rejects invalid parameter value types
echo "Test: Invalid parameter value types"
echo '{"key": 123}' > /tmp/bad-value.json
rm -rf /tmp/test-value
if "$ROOT_DIR/scripts/validate.sh" \
  --document-file "$TEST_DIR/test-doc.yaml" \
  --parameters-file /tmp/bad-value.json \
  --output-dir /tmp/test-value 2>/dev/null; then
  fail "Should reject non-string/array parameter values"
else
  pass "Rejects invalid parameter value types"
fi
rm -f /tmp/bad-value.json
rm -rf /tmp/test-value

rm -rf /tmp/test-out

[[ $FAILED -eq 0 ]] && echo "All tests passed" || echo "$FAILED test(s) failed"
exit $FAILED
