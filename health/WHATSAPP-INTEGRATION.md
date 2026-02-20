# VitalWhisper WhatsApp Integration

**Status:** ✅ Complete & Ready for Integration

## Overview

VitalWhisper is an automated WhatsApp-based blood pressure tracking system that:
- ✅ Auto-transcribes voice notes and attaches them to BP readings
- ✅ Auto-reads BP monitor photos using OpenAI Vision
- ✅ Sends confirmation replies with reading summaries
- ✅ Tracks stats and provides on-demand summaries

## Components

### 1. **whatsapp-handler.py** — Core Logic
Processes incoming messages and generates responses.

**Features:**
- `process_voice_note()` — Transcribe voice → attach to reading
- `process_bp_photo()` — Vision read photo → create reading
- `handle_incoming_message()` — Route messages by type
- Text commands: `stats`, `latest`, `help`

**Class:** `VitalWhisperHandler`

### 2. **whatsapp-automation.py** — OpenClaw Integration
Integrates handler with OpenClaw's message system.

**Features:**
- `send_reply()` — Send WhatsApp messages via OpenClaw
- `process_incoming_message()` — Full automation pipeline
- Simulation commands for testing

**Class:** `WhatsAppAutomation`

### 3. **Dependent Scripts**
- `process-voice-note.py` — Whisper transcription
- `process-bp-photo.py` — Vision-based BP reading
- `bp-tracker-nevo.py` — Data persistence & Excel export

---

## Integration with OpenClaw

### **Option 1: Use OpenClaw's Message Tool (Recommended)**

The main agent can invoke the automation directly:

```python
# In main session:
import subprocess
import json

result = subprocess.run([
    "python3", "/path/to/whatsapp-automation.py",
    "process",
    json.dumps({
        "type": "voice_note",
        "sender": "+905436782824",
        "file_path": "/tmp/voice.ogg"
    })
], capture_output=True, text=True)

response = json.loads(result.stdout)
print(response["send_status"])  # Check if message was sent
```

### **Option 2: Webhook Receiver (For Real WhatsApp Webhooks)**

If you want to auto-receive messages from WhatsApp Business API, create a webhook server:

```python
# Example Flask webhook server (run on port 8080)
from flask import Flask, request
import json
import subprocess

app = Flask(__name__)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    data = request.json
    
    # Extract message data
    messages = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
    
    for msg in messages:
        # Convert WhatsApp format to our format
        if msg.get("type") == "audio":
            # Download file and process
            ...
        
        # Call automation
        result = subprocess.run([
            "python3", "whatsapp-automation.py", "process",
            json.dumps(message_payload)
        ], capture_output=True, text=True)
    
    return {"status": "ok"}, 200
```

### **Option 3: OpenClaw Skill Integration**

Register as a skill in OpenClaw's plugin system:

```bash
# In ~/.openclaw/skills/vitalwhisper/
# skill.json + integration hooks
```

---

## Message Format

### Incoming Messages

**Voice Note:**
```json
{
    "type": "voice_note",
    "sender": "+905436782824",
    "file_path": "/tmp/voice.ogg",
    "language": "en",
    "timestamp": 1708353600
}
```

**BP Photo:**
```json
{
    "type": "photo",
    "sender": "+905436782824",
    "file_path": "/tmp/photo.jpg",
    "text": "Just checked at home",
    "timestamp": 1708353600
}
```

**Text Command:**
```json
{
    "type": "text",
    "sender": "+905436782824",
    "text": "stats",
    "timestamp": 1708353600
}
```

### Response Format

**Success Response:**
```json
{
    "status": "success",
    "type": "voice_note",
    "transcript": "I'm feeling good today",
    "reading_no": 42,
    "reading": {
        "systolic": 130,
        "diastolic": 83,
        "pulse": 53,
        "date": "2026-02-19",
        "time": "09:15"
    },
    "message": "✅ Voice note attached to reading #42: ...",
    "send_status": {
        "status": "sent",
        "to": "+905436782824"
    }
}
```

---

## Quick Start: Testing

### 1. **Test with Existing Files**

```bash
# Test voice transcription
python3 whatsapp-automation.py sim-voice /path/to/voice.ogg --sender +905436782824

# Test BP photo reading
python3 whatsapp-automation.py sim-photo /path/to/bp-monitor.jpg --notes "After morning meds"

# Test text command
python3 whatsapp-automation.py sim-text "stats"
```

### 2. **Simulate Full Automation**

```bash
# Create test message
python3 whatsapp-automation.py process '{"type":"text","sender":"+905436782824","text":"latest"}'

# Check output JSON for success/error
```

### 3. **Check Data**

```bash
# View current readings
cat health/bp-data.json | jq '.'

# Check Excel export
# → health/bp-readings.xlsx (auto-updated)
```

---

## Features by Message Type

### 📸 **BP Photo Processing**

Sends photo of BP monitor display → Auto-reads values + creates reading

**Supports:**
- JPEG, PNG
- Any BP monitor with digital display
- Low-confidence detection warning
- Automatic timestamp + notes

**Response:**
```
✅ Reading #42 recorded:
130/83 mmHg, 53 BPM
📅 2026-02-19 09:15
✓ Confidence: 98%
```

### 🎤 **Voice Note Processing**

Sends voice note → Auto-transcribe + attach to latest reading

**Supports:**
- OGG, MP4, MPEG
- Multiple languages (auto-detect or specify)
- Whisper skill integration
- Full transcription preserved in notes

**Response:**
```
✅ Voice note attached to reading #42:
2026-02-19 09:15 | 130/83/53 BPM

📝 Transcript: "Good reading after my walk, feeling great!"
```

### 💬 **Text Commands**

#### `stats` / `summary`
Show aggregated BP statistics:
```
📊 Blood Pressure Summary (42 readings):

Systolic (High):
  Avg: 127 mmHg
  Min: 118 | Max: 142

Diastolic (Low):
  Avg: 81 mmHg
  Min: 75 | Max: 88

Pulse:
  Avg: 61 BPM
  Min: 48 | Max: 73
```

#### `latest` / `last`
Show most recent reading:
```
📊 Latest reading (#42):
130/83 mmHg, 53 BPM
📅 2026-02-19 09:15
```

#### `help`
Show available commands.

---

## Data Persistence

All readings are stored in two formats:

1. **JSON** — `health/bp-data.json`
   - Machine-readable
   - All metadata + timestamps
   - Updated instantly

2. **Excel** — `health/bp-readings.xlsx`
   - Human-readable
   - Matches Nevo's original format
   - Auto-exported after each update

**Schema:**
```json
{
    "no": 42,
    "date": "2026-02-19",
    "time": "09:15",
    "beats": 53,
    "high": 130,
    "low": 83,
    "notes": "voice: Feeling good today | via photo OCR",
    "timestamp": "2026-02-19T09:15:00+03:00"
}
```

---

## Error Handling

### Voice Note Errors
- Missing Whisper skill → Error message
- Invalid audio format → Error message
- No readings exist yet → Helpful prompt

### Photo Errors
- Vision confidence < 0.7 → ⚠️ Warning flag
- Illegible display → Error message
- Invalid image → Error message

### Message Errors
- Unknown type → Error response
- Missing file → Error response
- API timeout → Retry suggestion

---

## Integration with Pedro (Main Agent)

### Monitor Incoming Messages

In Pedro's heartbeat or message handler:

```python
# Check for WhatsApp messages from Nevo
# If message is voice note or photo:
automation = WhatsAppAutomation()
result = automation.simulate_incoming_voice_note(file_path)

# Or dispatch directly:
# automation.process_incoming_message(json_data)
```

### Send Proactive Messages

```python
# Share daily summary
from health.whatsapp_handler import VitalWhisperHandler
handler = VitalWhisperHandler()
summary = handler.get_stats()

automation.send_reply(nevo_number, summary["message"])
```

### Log to Memory

Each automation result should be logged to `memory/YYYY-MM-DD.md`:

```markdown
## Health Automation
- Processed voice note: "Feeling good today" → Attached to reading #42
- Processed BP photo: 130/83/53 → High confidence
- Sent daily summary (42 readings, avg 127/81/61)
```

---

## Permissions & Security

✅ **Safe to automate:**
- Read BP data (Nevo's own data)
- Send WhatsApp replies to Nevo only
- Process locally (no external API calls except OpenAI Vision)

⚠️ **Requires approval:**
- Sending messages to other users
- Sharing BP data externally
- Changing data (should confirm first)

---

## Next Steps

1. **Test workflow** — Run simulations with test data
2. **Configure OpenClaw** — Set up message channel for WhatsApp
3. **Establish webhook** — If using WhatsApp Business API
4. **Enable automation** — Add to Pedro's heartbeat or cron
5. **Monitor & iterate** — Log results, refine prompts

---

## Files Checklist

- ✅ `whatsapp-handler.py` — Core logic
- ✅ `whatsapp-automation.py` — OpenClaw integration
- ✅ `process-voice-note.py` — Voice transcription
- ✅ `process-bp-photo.py` — Photo vision reading
- ✅ `bp-tracker-nevo.py` — Data storage
- ✅ `WHATSAPP-INTEGRATION.md` — This file

**Ready for integration with main session!**
