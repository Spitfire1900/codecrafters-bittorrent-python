#!/bin/bash

# Comprehensive CLI test suite for bencode decoder
# Tests the app directly without pytest

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_CMD="python3 $SCRIPT_DIR/app/main.py"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local input="$2"
    local expected_output="$3"
    local should_fail="${4:-false}"
    
    echo -n "Testing: $test_name ... "
    
    output=$($APP_CMD decode "$input" 2>&1)
    exit_code=$?
    
    if [ "$should_fail" = "true" ]; then
        if [ $exit_code -ne 0 ]; then
            echo -e "${GREEN}✓ PASS${NC} (correctly failed)"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC} (should have failed but didn't)"
            echo "  Input: $input"
            echo "  Output: $output"
            ((TESTS_FAILED++))
        fi
    else
        if [ $exit_code -eq 0 ]; then
            # Extract just the JSON output (last line)
            json_output=$(echo "$output" | tail -1)
            if [ "$json_output" = "$expected_output" ]; then
                echo -e "${GREEN}✓ PASS${NC}"
                ((TESTS_PASSED++))
            else
                echo -e "${RED}✗ FAIL${NC}"
                echo "  Input: $input"
                echo "  Expected: $expected_output"
                echo "  Got: $json_output"
                ((TESTS_FAILED++))
            fi
        else
            echo -e "${RED}✗ FAIL${NC} (unexpected error)"
            echo "  Input: $input"
            echo "  Output: $output"
            ((TESTS_FAILED++))
        fi
    fi
}

echo "=========================================="
echo "Bencode Decoder CLI Test Suite"
echo "=========================================="
echo ""

# BASIC STRING TESTS
echo "=== BASIC STRING TESTS ==="
run_test "Simple string" "5:hello" '"hello"'
run_test "String with numbers" "10:hello12345" '"hello12345"'
run_test "Empty string" "0:" '""'
run_test "Single character" "1:a" '"a"'
run_test "String with spaces" "11:hello world" '"hello world"'
echo ""

# BASIC INTEGER TESTS
echo "=== BASIC INTEGER TESTS ==="
run_test "Positive integer" "i42e" '42'
run_test "Zero" "i0e" '0'
run_test "Negative integer" "i-5e" '-5'
run_test "Large integer" "i123456789e" '123456789'
run_test "Negative large integer" "i-987654321e" '-987654321'
echo ""

# EMPTY AND SIMPLE LIST TESTS
echo "=== EMPTY AND SIMPLE LIST TESTS ==="
run_test "Empty list" "le" '[]'
run_test "List with one string" "l5:helloe" '["hello"]'
run_test "List with one integer" "li42ee" '[42]'
run_test "List with string and integer" "l5:helloi42ee" '["hello", 42]'
run_test "List with multiple strings" "l5:hello5:worlde" '["hello", "world"]'
run_test "List with multiple integers" "li1ei2ei3ee" '[1, 2, 3]'
echo ""

# NESTED LIST TESTS
echo "=== NESTED LIST TESTS ==="
run_test "One level nested empty" "llee" '[[]]'
run_test "One level nested with element" "ll5:helloee" '[["hello"]]'
run_test "Nested lists with multiple items" "lli1ei2eee" '[[1, 2]]'
run_test "Original failing case" "l5:helloi42el4:testee" '["hello", 42, ["test"]]'
run_test "String containing e" "l4:testee" '["test"]'
run_test "Multiple nested lists" "ll1:aeee" '[["a"]]'
run_test "Deeply nested lists" "llllleeeee" '[[[[[]]]]]'
run_test "Mixed nested structure" "li1el2:hiei99ee" '[1, ["hi"], 99]'
echo ""

# COMPLEX TESTS
echo "=== COMPLEX TESTS ==="
run_test "Complex nested with multiple elements" "li1el5:helloei99ee" '[1, ["hello"], 99]'
run_test "List starting with string containing digit" "l10:0123456789i99ee" '["0123456789", 99]'
run_test "List with single element" "l5:helloe" '["hello"]'
run_test "Nested list then integer" "lli1eei42ee" '[[1], 42]'
echo ""

# DICTIONARY TESTS
echo "=== DICTIONARY TESTS ==="
run_test "Empty dict" "de" '{}'
run_test "Simple key-value" "d3:key5:valuee" '{"key": "value"}'
run_test "Dict with integer" "d1:ai42ee" '{"a": 42}'
run_test "Dict with string" "d1:a5:helloe" '{"a": "hello"}'
run_test "Dict with list" "d1:al5:helloee" '{"a": ["hello"]}'
run_test "Dict with multiple keys" "d1:ai1e1:bi2ee" '{"a": 1, "b": 2}'
run_test "Nested dict" "d2:d1d3:key5:valueeee" '{"d1": {"key": "value"}}'
run_test "Dict with multi-element list" "d1:ali1ei2eee" '{"a": [1, 2]}'
run_test "Dict with list of dicts" "d1:ald1:a1:xeeee" '{"a": [{"a": "x"}]}'
echo ""

# ERROR CASES
echo "=== ERROR CASES (Should fail) ==="
run_test "Missing colon in string" "5hello" "" true
run_test "Missing closing 'e' for integer" "i42" "" true
run_test "Unclosed list" "l5:hello" "" true
run_test "Invalid character" "x5:hello" "" true
run_test "Empty input" "" "" true
run_test "Malformed integer" "iabce" "" true
run_test "String too long" "100:hello" "" true
run_test "Negative string length" "-5:hello" "" true
echo ""

# DEEP NESTING TESTS
echo "=== DEEP NESTING TESTS ==="
# Generate deeply nested list (100 levels)
deep_nested=$(python3 << 'PYTHON'
depth = 100
print("l" * depth + "e" * depth, end="")
PYTHON
)
run_test "100 levels of nesting" "$deep_nested" "$(python3 -c "print('[' * 100 + ']' * 100)")"
echo ""

# SUMMARY
echo "=========================================="
echo "Test Summary:"
echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
echo -e "  ${YELLOW}Skipped: $TESTS_SKIPPED${NC}"
echo "=========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
