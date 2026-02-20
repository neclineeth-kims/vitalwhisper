# VitalWhisper QuickStart — One-Minute Setup

## What Was Built

✅ **Complete WhatsApp automation for Nevo's BP tracking**
- Voice notes → Auto-transcribed + attached to readings
- BP monitor photos → Auto-detected values
- Text commands → Stats, latest reading, help
- Confirmation replies → Sent automatically via WhatsApp

## Try It Right Now

```bash
cd /home/raindrop/.openclaw/workspace

# Test 1: Help command
python3 health/whatsapp-automation.py sim-text "help"

# Test 2: Latest reading
python3 health/whatsapp-automation.py sim-text "latest"

# Test 3: Statistics
python3 health/whatsapp-automation.py sim-text "stats"
```

**Expected Output:** JSON with message + confirmation status

## Use in Your Code

```python
import subprocess, json

# Process any WhatsApp message
cmd = [
    "python3", 
    "health/whatsapp-automation.py", 
    "process",
    json.dumps({
        "type": "text",  # or "voice_note" or "photo"
        "sender": "+905436782824",
        "text": "stats"  # or "file_path": "/tmp/audio.ogg"
    })
]

result = subprocess.run(cmd, capture_output=True, text=True)
response = json.loads(result.stdout)

# Check if WhatsApp message was sent
if response["send_status"]["status"] == "sent":
    print("✅ Reply sent to Nevo")
```

## Features Ready Now

| Feature | Status | How to Use |
|---------|--------|-----------|
| Text commands | ✅ Ready | `sim-text "help"` |
| Latest reading | ✅ Ready | `sim-text "latest"` |
| Stats summary | ✅ Ready | `sim-text "stats"` |
| Voice notes | ⚠️ Ready* | `sim-voice /path/to/audio.ogg` |
| BP photos | ⚠️ Ready* | `sim-photo /path/to/image.jpg` |
| Data storage | ✅ Ready | Stored in `bp-data.json` + `bp-readings.xlsx` |

*Requires optional dependencies (OpenAI for photos, Whisper skill for voice)

## Current State

- **10 BP readings** stored from Nevo
- **Latest:** 137/87 mmHg, 55 BPM (2026-02-19 07:54)
- **Average:** 131.1/84.8 mmHg, 58.4 BPM
- **Excel export:** Auto-updated after each new reading

## 3-Step Integration

### Step 1: Add to Heartbeat (Optional)
```markdown
# HEARTBEAT.md
- VitalWhisper daily check: `python3 health/whatsapp-automation.py sim-text "stats"`
```

### Step 2: Add to Message Handler
When you receive WhatsApp message from Nevo:
```python
result = subprocess.run(
    ["python3", "health/whatsapp-automation.py", "process", json.dumps(message_data)],
    capture_output=True, text=True
)
response = json.loads(result.stdout)
# Message is already sent! (via send_status)
```

### Step 3: Log Results
```python
with open(f"memory/{date}.md", "a") as f:
    f.write(f"- VitalWhisper: {response['process_status']} {response['message_type']}\n")
```

## Files Reference

| File | Purpose | Size |
|------|---------|------|
| `whatsapp-handler.py` | Core logic | 11.8 KB |
| `whatsapp-automation.py` | OpenClaw integration | 7.7 KB |
| `INTEGRATION-GUIDE.md` | Full implementation guide | 8.1 KB |
| `WHATSAPP-INTEGRATION.md` | Complete API docs | 8.8 KB |
| `STATUS.md` | Detailed status + checklist | 5.7 KB |

## Message Format

### Input (any of these formats)

**Text command:**
```json
{
    "type": "text",
    "sender": "+905436782824",
    "text": "stats"
}
```

**Voice note:**
```json
{
    "type": "voice_note",
    "sender": "+905436782824",
    "file_path": "/tmp/voice.ogg"
}
```

**BP photo:**
```json
{
    "type": "photo",
    "sender": "+905436782824",
    "file_path": "/tmp/bp.jpg",
    "text": "After morning meds"
}
```

### Output

```json
{
    "process_status": "ok",           // success/error/partial
    "message_type": "text",           // type of message
    "processing_result": {
        "status": "ok",
        "message": "📊 Latest reading...",
        "reading": {...}
    },
    "send_status": {
        "status": "sent",             // Message sent to Nevo!
        "to": "+905436782824"
    }
}
```

## Need Help?

1. **Quick test:** `python3 health/whatsapp-automation.py sim-text "help"`
2. **See current readings:** `cat health/bp-data.json | jq '.'`
3. **Read full docs:** `health/INTEGRATION-GUIDE.md`
4. **Check status:** `health/STATUS.md`
5. **See all options:** `python3 health/whatsapp-automation.py -h`

---

**Status: ✅ COMPLETE & PRODUCTION READY**

All components tested and documented. Ready to integrate into main agent session.
