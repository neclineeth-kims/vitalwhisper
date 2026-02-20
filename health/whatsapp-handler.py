#!/usr/bin/env python3
"""
VitalWhisper WhatsApp Automation Handler
- Receives voice notes & BP photos via WhatsApp
- Auto-processes them (transcription + BP reading)
- Attaches to readings + sends confirmation replies
"""
import argparse
import json
import os
import pathlib
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

import importlib.util

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Import local modules
spec_voice = importlib.util.spec_from_file_location(
    "process_voice_note", SCRIPT_DIR / "process-voice-note.py"
)
process_voice_note = importlib.util.module_from_spec(spec_voice)
spec_voice.loader.exec_module(process_voice_note)

try:
    spec_photo = importlib.util.spec_from_file_location(
        "process_bp_photo", SCRIPT_DIR / "process-bp-photo.py"
    )
    process_bp_photo = importlib.util.module_from_spec(spec_photo)
    spec_photo.loader.exec_module(process_bp_photo)
    PHOTO_SUPPORT = True
except (ImportError, ModuleNotFoundError) as e:
    # Photo support requires OpenAI; gracefully degrade if not available
    process_bp_photo = None
    PHOTO_SUPPORT = False

spec_tracker = importlib.util.spec_from_file_location(
    "bp_tracker", SCRIPT_DIR / "bp-tracker-nevo.py"
)
bp_tracker = importlib.util.module_from_spec(spec_tracker)
spec_tracker.loader.exec_module(bp_tracker)


class VitalWhisperHandler:
    """Handle WhatsApp messages for VitalWhisper."""

    def __init__(self):
        self.tracker = bp_tracker.BPTracker()

    def process_voice_note(self, audio_path: str, sender: str, language: str = "en") -> dict:
        """
        Process a voice note message.
        
        Args:
            audio_path: Path to audio file (OGG/MP4/MPEG)
            sender: WhatsApp user ID or phone number
            language: Language hint for Whisper (default: en)
            
        Returns:
            dict with transcript, reading, and confirmation message
        """
        try:
            # Transcribe the voice note
            transcript = process_voice_note.transcribe(audio_path, language=language)
            
            # Attach to the latest BP reading
            updated_reading = process_voice_note.attach_voice_note(transcript)
            
            confirmation = {
                "status": "success",
                "type": "voice_note",
                "transcript": transcript,
                "reading_no": updated_reading["no"],
                "reading": {
                    "systolic": updated_reading["high"],
                    "diastolic": updated_reading["low"],
                    "pulse": updated_reading["beats"],
                    "date": updated_reading["date"],
                    "time": updated_reading["time"],
                },
                "message": (
                    f"✅ Voice note attached to reading #{updated_reading['no']}:\n"
                    f"{updated_reading['date']} {updated_reading['time']} | "
                    f"{updated_reading['high']}/{updated_reading['low']}/{updated_reading['beats']} "
                    f"BPM\n\n"
                    f"📝 Transcript: {transcript[:100]}{'...' if len(transcript) > 100 else ''}"
                ),
            }
            return confirmation

        except Exception as e:
            return {
                "status": "error",
                "type": "voice_note",
                "error": str(e),
                "message": f"❌ Failed to process voice note: {str(e)}",
            }

    def process_bp_photo(self, image_path: str, sender: str, notes: Optional[str] = None) -> dict:
        """
        Process a blood pressure photo.
        
        Args:
            image_path: Path to BP monitor photo (JPEG/PNG)
            sender: WhatsApp user ID or phone number
            notes: Optional user notes to attach
            
        Returns:
            dict with vision data, reading, and confirmation message
        """
        if not PHOTO_SUPPORT:
            return {
                "status": "error",
                "type": "bp_photo",
                "error": "Photo processing requires OpenAI module",
                "message": "❌ Photo processing not available (missing OpenAI dependency). Please ensure openai package is installed.",
            }
        
        try:
            result = process_bp_photo.add_reading_from_photo(image_path, note=notes)
            reading = result["reading"]
            vision = result["vision"]
            confidence = vision.get("confidence", 0)

            status = "success"
            if confidence < 0.7:
                status = "partial"

            confirmation = {
                "status": status,
                "type": "bp_photo",
                "reading_no": reading["no"],
                "reading": {
                    "systolic": reading["high"],
                    "diastolic": reading["low"],
                    "pulse": reading["beats"],
                    "date": reading["date"],
                    "time": reading["time"],
                },
                "confidence": confidence,
                "vision_notes": vision.get("notes", ""),
                "message": (
                    f"{'✅' if confidence >= 0.7 else '⚠️'} Reading #{reading['no']} recorded:\n"
                    f"{reading['high']}/{reading['low']} mmHg, {reading['beats']} BPM\n"
                    f"📅 {reading['date']} {reading['time']}\n"
                    f"{'🤔 Low confidence - please verify' if confidence < 0.7 else f'✓ Confidence: {confidence*100:.0f}%'}"
                ),
            }
            return confirmation

        except Exception as e:
            return {
                "status": "error",
                "type": "bp_photo",
                "error": str(e),
                "message": f"❌ Failed to process BP photo: {str(e)}",
            }

    def get_latest_reading_summary(self) -> dict:
        """Get summary of latest reading."""
        readings = self.tracker.readings
        if not readings:
            return {
                "status": "no_readings",
                "message": "No BP readings recorded yet. Send a photo or video of your monitor!",
            }

        latest = readings[-1]
        return {
            "status": "ok",
            "reading_no": latest["no"],
            "reading": {
                "systolic": latest["high"],
                "diastolic": latest["low"],
                "pulse": latest["beats"],
                "date": latest["date"],
                "time": latest["time"],
            },
            "message": (
                f"📊 Latest reading (#{latest['no']}):\n"
                f"{latest['high']}/{latest['low']} mmHg, {latest['beats']} BPM\n"
                f"📅 {latest['date']} {latest['time']}"
            ),
        }

    def get_stats(self) -> dict:
        """Get stats from tracker."""
        stats = self.tracker.get_stats()
        return {
            "status": "ok",
            "stats": stats,
            "message": self._format_stats_message(stats),
        }

    @staticmethod
    def _format_stats_message(stats: dict) -> str:
        """Format stats for WhatsApp message."""
        if not stats or stats.get("total_readings", 0) == 0:
            return "📊 No readings yet. Start by sending a BP photo!"

        count = stats.get("total_readings", 0)
        lines = [
            f"📊 Blood Pressure Summary ({count} readings):",
            f"",
            f"Systolic (High):",
            f"  Avg: {stats.get('recent_avg_systolic', 0):.0f} mmHg",
            f"",
            f"Diastolic (Low):",
            f"  Avg: {stats.get('recent_avg_diastolic', 0):.0f} mmHg",
            f"",
            f"Pulse:",
            f"  Avg: {stats.get('recent_avg_pulse', 0):.0f} BPM",
        ]
        
        # Add latest reading if available
        latest = stats.get("latest")
        if latest:
            lines.extend([
                f"",
                f"Latest: {latest['high']}/{latest['low']}/{latest['beats']} ({latest['date']} {latest['time']})",
            ])
        
        return "\n".join(lines)

    def handle_incoming_message(self, message_data: dict) -> dict:
        """
        Handle incoming WhatsApp message.
        
        Expected format:
        {
            "type": "voice_note" | "photo" | "text",
            "sender": "+905436782824",
            "file_path": "/path/to/file.ogg" (voice/photo),
            "text": "hello" (text),
            "language": "en" (optional, for voice),
        }
        """
        msg_type = message_data.get("type")
        sender = message_data.get("sender", "unknown")

        if msg_type == "voice_note":
            file_path = message_data.get("file_path")
            if not file_path or not os.path.exists(file_path):
                return {
                    "status": "error",
                    "message": "❌ No voice file found",
                }
            language = message_data.get("language", "en")
            return self.process_voice_note(file_path, sender, language)

        elif msg_type == "photo":
            file_path = message_data.get("file_path")
            if not file_path or not os.path.exists(file_path):
                return {
                    "status": "error",
                    "message": "❌ No photo file found",
                }
            notes = message_data.get("text", None)
            return self.process_bp_photo(file_path, sender, notes)

        elif msg_type == "text":
            text = message_data.get("text", "").strip().lower()

            # Command: "stats" or "summary"
            if text in ["stats", "summary", "📊"]:
                return self.get_stats()

            # Command: "latest" or "last"
            elif text in ["latest", "last", "📋"]:
                return self.get_latest_reading_summary()

            # Command: "help"
            elif text in ["help", "?"]:
                return {
                    "status": "ok",
                    "message": (
                        "🏥 VitalWhisper - Blood Pressure Tracker\n\n"
                        "Commands:\n"
                        "• Send a 📸 photo of your BP monitor → Auto-detect values\n"
                        "• Send a 🎤 voice note → Transcribed & attached to reading\n"
                        "• *stats* → Summary stats\n"
                        "• *latest* → Last reading\n"
                        "• *help* → This message"
                    ),
                }

            else:
                return {
                    "status": "ok",
                    "message": (
                        "👋 Welcome to VitalWhisper!\n\n"
                        "Send a 📸 photo of your BP monitor display, or a 🎤 voice note about your reading.\n"
                        "Type *help* for commands."
                    ),
                }

        else:
            return {
                "status": "error",
                "message": f"❌ Unknown message type: {msg_type}",
            }


def main():
    parser = argparse.ArgumentParser(
        description="VitalWhisper WhatsApp automation handler"
    )
    parser.add_argument("--voice", help="Process voice note (audio file path)")
    parser.add_argument("--photo", help="Process BP photo (image file path)")
    parser.add_argument("--text", help="Process text command")
    parser.add_argument("--sender", default="+905436782824", help="Sender phone number")
    parser.add_argument("--language", default="en", help="Language for voice transcription")
    parser.add_argument("--notes", help="Notes to attach (for photos)")
    parser.add_argument(
        "--json",
        help="JSON input (type, file_path, text, sender, language)",
    )

    args = parser.parse_args()

    handler = VitalWhisperHandler()

    if args.json:
        # Parse JSON input
        message_data = json.loads(args.json)
        result = handler.handle_incoming_message(message_data)
    elif args.voice:
        result = handler.process_voice_note(args.voice, args.sender, args.language)
    elif args.photo:
        result = handler.process_bp_photo(args.photo, args.sender, args.notes)
    elif args.text:
        result = handler.handle_incoming_message({
            "type": "text",
            "text": args.text,
            "sender": args.sender,
        })
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
