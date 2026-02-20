#!/usr/bin/env python3
"""
VitalWhisper WhatsApp Listener Hook
- Intercepts incoming WhatsApp messages
- Routes to VitalWhisper handler
- Logs all interactions
"""
import json
import logging
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Configuration
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
NEVO_NUMBER = "+905436782824"
AUTOMATION_SCRIPT = SCRIPT_DIR / "whatsapp-automation.py"
LOG_FILE = SCRIPT_DIR / "listener-events.log"
DATA_DIR = SCRIPT_DIR

# Message processing timeouts (seconds)
TIMEOUTS = {
    "voice_note": 60,
    "photo": 30,
    "text": 10,
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class WhatsAppListenerHook:
    """Hook listener for incoming WhatsApp messages."""

    def __init__(self):
        self.nevo_number = NEVO_NUMBER
        self.automation_script = AUTOMATION_SCRIPT
        self.log_file = LOG_FILE
        self.message_count = 0
        self.success_count = 0
        self.error_count = 0

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp message.
        
        Args:
            message_data: Dict with keys: type, sender, file_path/text, timestamp
            
        Returns:
            Result dict with processing status
        """
        self.message_count += 1
        
        # Validate message format
        message_type = message_data.get("type", "text").lower()
        sender = message_data.get("sender", self.nevo_number)
        
        # Only process messages from Nevo (for security)
        if sender != self.nevo_number:
            logger.warning(f"Ignoring message from unknown sender: {sender}")
            return {
                "status": "ignored",
                "reason": "not_nevo",
                "sender": sender,
            }
        
        logger.info(f"Processing incoming {message_type} from {sender}")
        
        # Timeout for this message type
        timeout = TIMEOUTS.get(message_type, 10)
        
        try:
            # Call whatsapp-automation.py with JSON message
            result = self._process_with_automation(message_data, timeout)
            
            if result.get("process_status") == "success":
                self.success_count += 1
                logger.info(f"✅ Message processed successfully")
            else:
                self.error_count += 1
                logger.warning(f"⚠️ Message processed with status: {result.get('process_status')}")
            
            return result
            
        except subprocess.TimeoutExpired:
            self.error_count += 1
            logger.error(f"❌ Processing timeout after {timeout}s")
            return {
                "status": "timeout",
                "type": message_type,
                "sender": sender,
            }
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Processing error: {str(e)}")
            return {
                "status": "error",
                "type": message_type,
                "sender": sender,
                "error": str(e),
            }

    def _process_with_automation(self, message_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Call whatsapp-automation.py to process message."""
        cmd = [
            "python3",
            str(self.automation_script),
            "process",
            json.dumps(message_data),
        ]
        
        logger.debug(f"Executing: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRIPT_DIR),
        )
        
        if result.returncode != 0:
            logger.error(f"Automation script error: {result.stderr}")
            return {
                "status": "error",
                "error": result.stderr or result.stdout,
            }
        
        try:
            response = json.loads(result.stdout)
            return response
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            logger.error(f"Raw output: {result.stdout}")
            return {
                "status": "error",
                "error": f"Invalid JSON response: {str(e)}",
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get listener statistics."""
        return {
            "total_messages": self.message_count,
            "successful": self.success_count,
            "errors": self.error_count,
            "success_rate": (
                100 * self.success_count / self.message_count
                if self.message_count > 0
                else 0
            ),
        }

    def log_message_event(self, message_data: Dict[str, Any], result: Dict[str, Any]):
        """Log message event to structured JSON log."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "sender": message_data.get("sender"),
            "type": message_data.get("type"),
            "status": result.get("process_status") or result.get("status"),
            "processing_time": result.get("processing_time", 0),
            "result": result,
        }
        
        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def handle_incoming_message(message_json: str) -> Dict[str, Any]:
    """
    Main entry point for listener hook.
    
    Called when OpenClaw receives a WhatsApp message.
    
    Args:
        message_json: JSON string with message data
        
    Returns:
        Result dict
    """
    try:
        message_data = json.loads(message_json)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error": f"Invalid JSON: {str(e)}",
        }
    
    hook = WhatsAppListenerHook()
    result = hook.handle_message(message_data)
    hook.log_message_event(message_data, result)
    
    return result


def main():
    """Command-line interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="VitalWhisper WhatsApp Listener Hook"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Handle incoming message
    handle_parser = subparsers.add_parser("handle", help="Handle incoming message")
    handle_parser.add_argument("message_json", help="Message JSON string")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show listener stats")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run smoke tests")
    
    args = parser.parse_args()
    
    if args.command == "handle":
        result = handle_incoming_message(args.message_json)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stats":
        hook = WhatsAppListenerHook()
        # In a real scenario, stats would be loaded from log file
        print(json.dumps(hook.get_stats(), indent=2))
    
    elif args.command == "test":
        # Run smoke tests
        print("🧪 Running smoke tests...\n")
        
        hook = WhatsAppListenerHook()
        
        # Test 1: Text command
        print("Test 1: Text command (stats)")
        test_msg_1 = json.dumps({
            "type": "text",
            "sender": NEVO_NUMBER,
            "text": "stats",
            "timestamp": int(time.time()),
        })
        result_1 = handle_incoming_message(test_msg_1)
        print(f"Status: {result_1.get('process_status', result_1.get('status'))}\n")
        
        # Test 2: Text command
        print("Test 2: Text command (latest)")
        test_msg_2 = json.dumps({
            "type": "text",
            "sender": NEVO_NUMBER,
            "text": "latest",
            "timestamp": int(time.time()),
        })
        result_2 = handle_incoming_message(test_msg_2)
        print(f"Status: {result_2.get('process_status', result_2.get('status'))}\n")
        
        # Test 3: Unknown sender (should be ignored)
        print("Test 3: Message from unknown sender (should be ignored)")
        test_msg_3 = json.dumps({
            "type": "text",
            "sender": "+1234567890",
            "text": "hack attempt",
            "timestamp": int(time.time()),
        })
        result_3 = handle_incoming_message(test_msg_3)
        print(f"Status: {result_3.get('status')} (reason: {result_3.get('reason')})\n")
        
        print("✅ Smoke tests complete!")
        print(f"Stats: {hook.get_stats()}")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
