#!/usr/bin/env python3
"""
VitalWhisper WhatsApp Automation Integration with OpenClaw
- Listens for WhatsApp messages via OpenClaw message API
- Processes voice notes & photos
- Sends automated confirmations
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Optional

import importlib.util

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Import the WhatsApp handler
spec = importlib.util.spec_from_file_location(
    "whatsapp_handler", SCRIPT_DIR / "whatsapp-handler.py"
)
whatsapp_handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(whatsapp_handler_module)

VitalWhisperHandler = whatsapp_handler_module.VitalWhisperHandler


class WhatsAppAutomation:
    """Integrate VitalWhisper with OpenClaw's message system."""

    def __init__(self, nevo_number: str = "+905436782824"):
        """
        Initialize WhatsApp automation.
        
        Args:
            nevo_number: Nevo's WhatsApp number (default: from TOOLS.md)
        """
        self.nevo_number = nevo_number
        self.handler = VitalWhisperHandler()

    def send_reply(self, to_number: str, message: str) -> dict:
        """
        Send a WhatsApp reply via OpenClaw message API.
        
        Uses the `message` tool (OpenClaw's unified messaging system).
        """
        # Build the OpenClaw message command
        cmd = [
            "openclaw",
            "message",
            "send",
            "--channel", "whatsapp",
            "--target", to_number,
            "--message", message,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                return {
                    "status": "sent",
                    "to": to_number,
                    "message_preview": message[:50] + "..." if len(message) > 50 else message,
                }
            else:
                return {
                    "status": "error",
                    "to": to_number,
                    "error": result.stderr or result.stdout,
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "to": to_number,
            }
        except Exception as e:
            return {
                "status": "error",
                "to": to_number,
                "error": str(e),
            }

    def process_incoming_message(self, message_json: str) -> dict:
        """
        Process incoming WhatsApp message and send confirmation.
        
        Expected message format:
        {
            "type": "voice_note" | "photo" | "text",
            "sender": "+905436782824",
            "message_id": "wamid.xxx",
            "file_path": "/tmp/voice.ogg",  (for voice/photo)
            "text": "hello",                 (for text)
            "timestamp": 1708353600,
        }
        """
        try:
            message_data = json.loads(message_json)
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"Invalid JSON: {str(e)}",
            }

        sender = message_data.get("sender", self.nevo_number)
        message_type = message_data.get("type", "text")

        # Process the message with the handler
        result = self.handler.handle_incoming_message(message_data)

        # Extract confirmation message
        confirmation_msg = result.get("message", "")
        status = result.get("status", "unknown")

        # Send confirmation reply
        send_status = self.send_reply(sender, confirmation_msg)

        # Return full result
        return {
            "process_status": status,
            "message_type": message_type,
            "processing_result": result,
            "send_status": send_status,
            "timestamp": time.time(),
        }

    def simulate_incoming_voice_note(self, audio_path: str, sender: str = None) -> dict:
        """Simulate receiving a voice note for testing."""
        if not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        sender = sender or self.nevo_number
        message_json = json.dumps({
            "type": "voice_note",
            "sender": sender,
            "file_path": audio_path,
            "timestamp": time.time(),
        })
        return self.process_incoming_message(message_json)

    def simulate_incoming_photo(self, image_path: str, notes: str = None, sender: str = None) -> dict:
        """Simulate receiving a BP photo for testing."""
        if not os.path.exists(image_path):
            return {"status": "error", "message": f"Image file not found: {image_path}"}

        sender = sender or self.nevo_number
        message_json = json.dumps({
            "type": "photo",
            "sender": sender,
            "file_path": image_path,
            "text": notes,
            "timestamp": time.time(),
        })
        return self.process_incoming_message(message_json)

    def simulate_incoming_text(self, text: str, sender: str = None) -> dict:
        """Simulate receiving a text command for testing."""
        sender = sender or self.nevo_number
        message_json = json.dumps({
            "type": "text",
            "sender": sender,
            "text": text,
            "timestamp": time.time(),
        })
        return self.process_incoming_message(message_json)


def main():
    parser = argparse.ArgumentParser(
        description="VitalWhisper WhatsApp Automation (OpenClaw Integration)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Process incoming WhatsApp message (JSON)"
    )
    process_parser.add_argument("message_json", help="Message JSON string")

    # Simulate commands
    sim_voice = subparsers.add_parser("sim-voice", help="Simulate voice note")
    sim_voice.add_argument("audio_path", help="Audio file path")
    sim_voice.add_argument("--sender", help="Sender number (default: Nevo)")

    sim_photo = subparsers.add_parser("sim-photo", help="Simulate BP photo")
    sim_photo.add_argument("image_path", help="Image file path")
    sim_photo.add_argument("--notes", help="Optional notes")
    sim_photo.add_argument("--sender", help="Sender number (default: Nevo)")

    sim_text = subparsers.add_parser("sim-text", help="Simulate text command")
    sim_text.add_argument("text", help="Text message")
    sim_text.add_argument("--sender", help="Sender number (default: Nevo)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    automation = WhatsAppAutomation()

    if args.command == "process":
        result = automation.process_incoming_message(args.message_json)
    elif args.command == "sim-voice":
        result = automation.simulate_incoming_voice_note(
            args.audio_path,
            sender=args.sender,
        )
    elif args.command == "sim-photo":
        result = automation.simulate_incoming_photo(
            args.image_path,
            notes=args.notes,
            sender=args.sender,
        )
    elif args.command == "sim-text":
        result = automation.simulate_incoming_text(
            args.text,
            sender=args.sender,
        )
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
