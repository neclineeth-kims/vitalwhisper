#!/usr/bin/env python3
"""Transcribe a voice note and attach it to a BP reading."""
import argparse
import json
import os
import pathlib
import subprocess
import tempfile
from datetime import datetime

import importlib.util

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
BP_TRACKER_PATH = SCRIPT_DIR / "bp-tracker-nevo.py"

spec = importlib.util.spec_from_file_location("bp_tracker", BP_TRACKER_PATH)
bp_tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp_tracker)

WHISPER_SCRIPT = pathlib.Path(
    "/home/raindrop/.nvm/versions/node/v24.13.0/lib/node_modules/openclaw/skills/openai-whisper-api/scripts/transcribe.sh"
)


def transcribe(audio_path: str, language: str | None = None) -> str:
    """Call the Whisper skill script and return transcript text."""
    if not WHISPER_SCRIPT.exists():
        raise RuntimeError("Whisper skill script not found")

    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    out_file.close()

    cmd = [
        str(WHISPER_SCRIPT),
        audio_path,
        "--out",
        out_file.name,
    ]
    if language:
        cmd.extend(["--language", language])

    subprocess.run(cmd, check=True)

    with open(out_file.name, "r", encoding="utf-8") as f:
        text = f.read().strip()

    os.unlink(out_file.name)
    return text


def attach_voice_note(transcript: str, reading_no: int | None = None) -> dict:
    tracker = bp_tracker.BPTracker()
    readings = tracker.readings
    if not readings:
        raise RuntimeError("No readings exist yet")

    target = None
    if reading_no is not None:
        for reading in readings:
            if reading["no"] == reading_no:
                target = reading
                break
        if target is None:
            raise RuntimeError(f"Reading #{reading_no} not found")
    else:
        target = readings[-1]

    note_prefix = "voice: "
    existing = target.get("notes", "").strip()
    if existing:
        new_notes = f"{existing} | {note_prefix}{transcript}"
    else:
        new_notes = f"{note_prefix}{transcript}"

    target["notes"] = new_notes
    tracker.save_data()
    tracker.export_to_excel()

    return target


def main():
    parser = argparse.ArgumentParser(description="Process voice note")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--reading", type=int, help="Reading number to attach to")
    parser.add_argument("--language", help="Force language for Whisper")
    args = parser.parse_args()

    transcript = transcribe(args.audio, args.language)
    updated = attach_voice_note(transcript, args.reading)

    print(json.dumps({"transcript": transcript, "reading": updated}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
