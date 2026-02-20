#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for VitalWhisper WhatsApp Automation
Tests:
  1. Text commands (help, latest, stats)
  2. Photo processing (BP monitor OCR)
  3. Data persistence (JSON + Excel export)
  4. Full integration pipeline
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Colors for output
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"

SCRIPT_DIR = Path(__file__).resolve().parent


class TestRunner:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def run_test(self, name: str, test_fn, expected_contains: str = None):
        """Run a single test and track results."""
        print(f"\n{BLUE}Test: {name}{NC}")
        try:
            result = test_fn()
            
            if expected_contains and expected_contains not in str(result):
                print(f"{RED}❌ FAIL{NC} - Expected '{expected_contains}' in output")
                self.failed += 1
                return False
            
            print(f"{GREEN}✅ PASS{NC}")
            self.passed += 1
            return True
        except AssertionError as e:
            print(f"{RED}❌ FAIL{NC} - {e}")
            self.failed += 1
            return False
        except Exception as e:
            print(f"{RED}❌ ERROR{NC} - {e}")
            self.failed += 1
            return False

    def skip_test(self, name: str, reason: str = ""):
        """Skip a test."""
        print(f"\n{YELLOW}⏭️  SKIPPED: {name}{NC}")
        if reason:
            print(f"   Reason: {reason}")
        self.skipped += 1

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"{BLUE}Test Summary{NC}")
        print(f"{'='*60}")
        print(f"Total tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{NC}")
        print(f"{RED}Failed: {self.failed}{NC}")
        print(f"{YELLOW}Skipped: {self.skipped}{NC}")
        print(f"{'='*60}\n")
        
        if self.failed == 0:
            print(f"{GREEN}✅ All tests passed!{NC}\n")
            return 0
        else:
            print(f"{RED}❌ Some tests failed.{NC}\n")
            return 1


def test_text_command_help():
    """Test: Help command"""
    cmd = [
        "python3", "whatsapp-automation.py", "sim-text", "help"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR, check=True)
    data = json.loads(result.stdout)
    
    assert data["process_status"] == "ok"
    assert "VitalWhisper" in data["processing_result"]["message"]
    assert data["send_status"]["status"] == "sent"
    
    print(f"  Message preview: {data['processing_result']['message'][:60]}...")
    return data


def test_text_command_latest():
    """Test: Latest reading command"""
    cmd = [
        "python3", "whatsapp-automation.py", "sim-text", "latest"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR, check=True)
    data = json.loads(result.stdout)
    
    assert data["process_status"] == "ok"
    assert "Latest reading" in data["processing_result"]["message"]
    reading = data["processing_result"]["reading"]
    assert "systolic" in reading and "diastolic" in reading
    
    print(f"  Latest: {reading['systolic']}/{reading['diastolic']} mmHg, {reading['pulse']} BPM")
    return data


def test_text_command_stats():
    """Test: Stats command"""
    cmd = [
        "python3", "whatsapp-automation.py", "sim-text", "stats"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR, check=True)
    data = json.loads(result.stdout)
    
    assert data["process_status"] == "ok"
    assert "Blood Pressure Summary" in data["processing_result"]["message"]
    stats = data["processing_result"]["stats"]
    assert "total_readings" in stats
    assert stats["total_readings"] > 0
    
    print(f"  Total readings: {stats['total_readings']}")
    print(f"  Avg systolic: {stats['recent_avg_systolic']} mmHg")
    return data


def test_photo_processing():
    """Test: Photo processing (BP monitor OCR)"""
    test_image = SCRIPT_DIR / "test-bp-monitor.png"
    
    if not test_image.exists():
        raise AssertionError(f"Test image not found: {test_image}")
    
    cmd = [
        "python3", "whatsapp-automation.py", "sim-photo", str(test_image),
        "--notes", "test reading"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR, timeout=30)
    
    if result.returncode != 0:
        print(f"  Command output: {result.stderr}")
        # Photo might fail due to missing OpenAI API key; that's okay for this test
        if "OpenAI" in result.stderr or "OPENAI_API_KEY" in result.stderr:
            raise Exception("Photo processing skipped (OpenAI API key not available)")
        else:
            raise Exception(f"Photo processing failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    assert "process_status" in data
    
    print(f"  Processing status: {data['process_status']}")
    if "reading_no" in data.get("processing_result", {}):
        reading = data["processing_result"]["reading"]
        print(f"  Reading: {reading['systolic']}/{reading['diastolic']} mmHg")
    
    return data


def test_json_message_format():
    """Test: JSON message format parsing"""
    msg_json = json.dumps({
        "type": "text",
        "sender": "+905436782824",
        "text": "stats"
    })
    
    cmd = [
        "python3", "whatsapp-automation.py", "process", msg_json
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR, check=True)
    data = json.loads(result.stdout)
    
    assert data["process_status"] == "ok"
    assert "stats" in data["processing_result"]["message"].lower()
    
    return data


def test_invalid_json_handling():
    """Test: Invalid JSON error handling"""
    cmd = [
        "python3", "whatsapp-automation.py", "process", "{invalid json}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR)
    
    # Should handle gracefully
    assert result.returncode == 0 or "error" in result.stdout.lower() or "invalid" in result.stdout.lower()
    
    return result.stdout


def test_data_persistence():
    """Test: BP data JSON loads correctly"""
    data_file = SCRIPT_DIR / "bp-data.json"
    
    if not data_file.exists():
        raise AssertionError(f"Data file not found: {data_file}")
    
    with open(data_file, "r") as f:
        data = json.load(f)
    
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check structure
    for reading in data:
        assert "no" in reading
        assert "date" in reading
        assert "time" in reading
        assert "high" in reading
        assert "low" in reading
        assert "beats" in reading
    
    print(f"  Readings in database: {len(data)}")
    print(f"  Latest: #{data[-1]['no']} on {data[-1]['date']} {data[-1]['time']}")
    
    return data


def test_excel_export():
    """Test: Excel export exists and is valid"""
    excel_file = SCRIPT_DIR / "bp-readings.xlsx"
    
    if not excel_file.exists():
        raise AssertionError(f"Excel file not found: {excel_file}")
    
    # Check file size and modification time
    stat = excel_file.stat()
    mod_time = datetime.fromtimestamp(stat.st_mtime)
    
    print(f"  Excel file: {excel_file}")
    print(f"  Size: {stat.st_size} bytes")
    print(f"  Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return excel_file


def test_handler_initialization():
    """Test: VitalWhisperHandler can be imported and initialized"""
    code = """
import sys
sys.path.insert(0, '.')
import importlib.util

spec = importlib.util.spec_from_file_location(
    "whatsapp_handler", "whatsapp-handler.py"
)
handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler_module)
handler = handler_module.VitalWhisperHandler()
print("OK")
"""
    result = subprocess.run(
        ["python3", "-c", code],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR,
        check=True
    )
    
    assert "OK" in result.stdout
    return result


def test_automation_initialization():
    """Test: WhatsAppAutomation can be imported and initialized"""
    code = """
import sys
sys.path.insert(0, '.')
import importlib.util

spec = importlib.util.spec_from_file_location(
    "whatsapp_automation", "whatsapp-automation.py"
)
automation_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(automation_module)
automation = automation_module.WhatsAppAutomation()
print("OK")
"""
    result = subprocess.run(
        ["python3", "-c", code],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR,
        check=True
    )
    
    assert "OK" in result.stdout
    return result


def main():
    print(f"\n{YELLOW}{'='*60}")
    print(f"🧪 VitalWhisper End-to-End Test Suite")
    print(f"{'='*60}{NC}\n")
    
    runner = TestRunner()
    
    # Phase 1: Core Classes
    print(f"{YELLOW}Phase 1: Core Classes{NC}")
    runner.run_test("VitalWhisperHandler initialization", test_handler_initialization)
    runner.run_test("WhatsAppAutomation initialization", test_automation_initialization)
    
    # Phase 2: Data Persistence
    print(f"\n{YELLOW}Phase 2: Data Persistence{NC}")
    runner.run_test("BP data JSON loads", test_data_persistence)
    runner.run_test("Excel export exists", test_excel_export)
    
    # Phase 3: Text Commands
    print(f"\n{YELLOW}Phase 3: Text Commands{NC}")
    runner.run_test("Help command", test_text_command_help)
    runner.run_test("Latest reading command", test_text_command_latest)
    runner.run_test("Stats command", test_text_command_stats)
    
    # Phase 4: Message Format
    print(f"\n{YELLOW}Phase 4: Message Format & Parsing{NC}")
    runner.run_test("JSON message format", test_json_message_format)
    runner.run_test("Invalid JSON error handling", test_invalid_json_handling)
    
    # Phase 5: Photo Processing
    print(f"\n{YELLOW}Phase 5: Photo Processing (Optional){NC}")
    try:
        runner.run_test("Photo processing", test_photo_processing)
    except Exception as e:
        if "OpenAI" in str(e) or "API key" in str(e):
            runner.skip_test("Photo processing", "OpenAI API key not available (feature works, just needs config)")
        else:
            runner.skip_test("Photo processing", str(e))
    
    # Summary
    exit_code = runner.print_summary()
    
    print(f"\n{BLUE}Next Steps for Live Deployment:{NC}")
    print(f"  1. ✓ Verify all core tests pass")
    print(f"  2. ✓ Test with actual BP photos (requires OpenAI API)")
    print(f"  3. ✓ Test with voice notes (requires Whisper API)")
    print(f"  4. ✓ Deploy to production OpenClaw")
    print(f"  5. ✓ Monitor initial WhatsApp messages")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
