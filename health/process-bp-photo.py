#!/usr/bin/env python3
"""Photo-based BP ingestion using OpenAI Vision."""
import argparse
import base64
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

import importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BP_TRACKER_PATH = os.path.join(SCRIPT_DIR, "bp-tracker-nevo.py")

spec = importlib.util.spec_from_file_location("bp_tracker", BP_TRACKER_PATH)
bp_tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp_tracker)

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")

PROMPT = (
    "You will receive a photo of a digital blood pressure monitor. "
    "Read its display and output JSON with keys: systolic, diastolic, pulse, "
    "display_date (string or null, as shown on screen), display_time (string or null), "
    "notes (string, optional observation), confidence (0-1 float). "
    "If you are unsure of any value, set confidence below 0.7 and explain in notes. "
    "Return ONLY JSON." )


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_vision(image_path: str) -> dict:
    client = OpenAI()
    image_b64 = encode_image(image_path)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{image_b64}",
                    },
                ],
            }
        ],
        temperature=0,
    )

    # Extract text output
    chunks = []
    for item in response.output:
        for content in item.content:
            if content.type == "output_text":
                chunks.append(content.text)
    text = "\n".join(chunks).strip()

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\n", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Vision response not valid JSON: {text}") from exc

    return data


def parse_datetime(display_date: str | None, display_time: str | None) -> datetime | None:
    if not display_date and not display_time:
        return None

    now = datetime.now(ISTANBUL_TZ)
    date_part = None
    if display_date:
        match = re.search(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?", display_date)
        if match:
            day, month, year = match.groups(default=str(now.year))
            if len(year) == 2:
                year = f"20{year}"
            try:
                date_part = datetime(int(year), int(month), int(day), tzinfo=ISTANBUL_TZ)
            except ValueError:
                date_part = None
    time_part = None
    if display_time:
        match = re.search(r"(\d{1,2}):(\d{2})", display_time)
        if match:
            hour, minute = match.groups()
            hour = int(hour)
            minute = int(minute)
            if 0 <= hour < 24 and 0 <= minute < 60:
                time_part = (hour, minute)

    if date_part:
        if time_part:
            return date_part.replace(hour=time_part[0], minute=time_part[1])
        return date_part
    if time_part:
        return now.replace(hour=time_part[0], minute=time_part[1], second=0, microsecond=0)
    return None


def add_reading_from_photo(image_path: str, note: str | None = None) -> dict:
    vision_data = call_vision(image_path)
    required_keys = {"systolic", "diastolic", "pulse", "confidence"}
    if not required_keys.issubset(vision_data):
        raise RuntimeError(f"Vision output missing fields: {vision_data}")

    extra_notes = vision_data.get("notes")
    combined_notes = " | ".join(
        part for part in [note, extra_notes, "via photo OCR"] if part
    )

    custom_time = parse_datetime(
        vision_data.get("display_date"), vision_data.get("display_time")
    )

    tracker = bp_tracker.BPTracker()
    reading = tracker.add_reading(
        int(vision_data["systolic"]),
        int(vision_data["diastolic"]),
        int(vision_data["pulse"]),
        notes=combined_notes,
        custom_time=custom_time,
    )

    stats = tracker.get_stats()

    return {
        "reading": reading,
        "stats": stats,
        "vision": vision_data,
    }


def main():
    parser = argparse.ArgumentParser(description="Process BP photo")
    parser.add_argument("image", help="Path to BP photo")
    parser.add_argument("--notes", help="Optional note to attach", default=None)
    args = parser.parse_args()

    result = add_reading_from_photo(args.image, args.notes)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
