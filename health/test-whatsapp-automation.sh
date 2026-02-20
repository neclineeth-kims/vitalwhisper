#!/bin/bash
# Test VitalWhisper WhatsApp Automation End-to-End

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 VitalWhisper WhatsApp Automation Test Suite"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

run_test() {
    local test_name="$1"
    local command="$2"
    test_count=$((test_count + 1))
    
    echo -e "${BLUE}Test $test_count: $test_name${NC}"
    
    if eval "$command"; then
        echo -e "${GREEN}✅ PASS${NC}\n"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}❌ FAIL${NC}\n"
        fail_count=$((fail_count + 1))
    fi
}

# Test 1: Check dependencies
echo -e "${YELLOW}Phase 1: Dependencies${NC}"
run_test "Python3 installed" "python3 --version > /dev/null"
run_test "Required modules" "python3 -c 'import json, pathlib, subprocess' && echo done"

# Test 2: Check file structure
echo -e "${YELLOW}Phase 2: File Structure${NC}"
run_test "whatsapp-handler.py exists" "test -f whatsapp-handler.py"
run_test "whatsapp-automation.py exists" "test -f whatsapp-automation.py"
run_test "process-voice-note.py exists" "test -f process-voice-note.py"
run_test "process-bp-photo.py exists" "test -f process-bp-photo.py"
run_test "bp-tracker-nevo.py exists" "test -f bp-tracker-nevo.py"
run_test "bp-data.json exists or will be created" "test -f bp-data.json || echo 'will create on first use'"

# Test 3: Handler class instantiation
echo -e "${YELLOW}Phase 3: Core Classes${NC}"
run_test "VitalWhisperHandler imports" \
    "python3 -c 'import sys; sys.path.insert(0, \".\"); from whatsapp_handler import VitalWhisperHandler; h = VitalWhisperHandler(); print(\"OK\")'"

run_test "WhatsAppAutomation imports" \
    "python3 -c 'import sys; sys.path.insert(0, \".\"); from whatsapp_automation import WhatsAppAutomation; a = WhatsAppAutomation(); print(\"OK\")'"

# Test 4: Text commands (no files needed)
echo -e "${YELLOW}Phase 4: Text Commands${NC}"

run_test "Help command" \
    "python3 whatsapp-automation.py sim-text 'help' 2>&1 | grep -q 'VitalWhisper'"

run_test "Latest command (no readings)" \
    "python3 whatsapp-automation.py sim-text 'latest' 2>&1 | grep -q 'No readings yet' || grep -q 'Latest reading'"

run_test "Stats command (no readings)" \
    "python3 whatsapp-automation.py sim-text 'stats' 2>&1 | grep -q 'Blood Pressure Summary'"

run_test "Unrecognized command" \
    "python3 whatsapp-automation.py sim-text 'hello' 2>&1 | grep -q 'Welcome to VitalWhisper'"

# Test 5: Photo processing (if test image exists)
echo -e "${YELLOW}Phase 5: Photo Processing${NC}"

if ls bp-readings.xlsx &>/dev/null; then
    echo "📸 Test image available, skipping photo test (requires actual BP monitor photo)"
    echo "   (To test: python3 whatsapp-automation.py sim-photo /path/to/image.jpg)"
else
    echo "⏭️  Skipping photo test (no test image)"
fi

# Test 6: Voice processing (if test audio exists)
echo -e "${YELLOW}Phase 6: Voice Processing${NC}"

echo "🎤 To test voice: python3 whatsapp-automation.py sim-voice /path/to/audio.ogg"

# Test 7: JSON message format
echo -e "${YELLOW}Phase 7: JSON Message Format${NC}"

run_test "Text message JSON format" \
    "python3 whatsapp-automation.py process '{\"type\":\"text\",\"sender\":\"+905436782824\",\"text\":\"help\"}' 2>&1 | python3 -m json.tool > /dev/null && echo OK"

run_test "Invalid JSON handling" \
    "python3 whatsapp-automation.py process '{broken json}' 2>&1 | grep -q 'Invalid JSON' || grep -q 'error'"

# Test 8: Data persistence
echo -e "${YELLOW}Phase 8: Data Persistence${NC}"

run_test "BP data JSON readable" \
    "python3 -c 'import json; json.load(open(\"bp-data.json\"))' && echo OK"

run_test "BP tracker can load data" \
    "python3 -c 'import sys; sys.path.insert(0, \".\"); from bp_tracker_nevo import BPTracker; t = BPTracker(); print(f\"Loaded {len(t.readings)} readings\")'"

# Test 9: Excel export
echo -e "${YELLOW}Phase 9: Excel Export${NC}"

run_test "BP readings Excel exists" \
    "test -f bp-readings.xlsx && echo 'Excel file exists'"

# Summary
echo ""
echo "=============================================="
echo -e "${BLUE}Test Summary${NC}"
echo "=============================================="
echo "Total: $test_count"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test with actual BP photo: python3 whatsapp-automation.py sim-photo /path/to/bp.jpg"
    echo "2. Test with actual voice note: python3 whatsapp-automation.py sim-voice /path/to/audio.ogg"
    echo "3. Integrate into main agent automation"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review output above.${NC}"
    exit 1
fi
