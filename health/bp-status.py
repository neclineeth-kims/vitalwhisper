#!/usr/bin/env python3
"""
Quick BP status check for Pedro
"""

import sys
import os
import importlib.util

# Load the BP tracker module
spec = importlib.util.spec_from_file_location("bp_tracker", os.path.join(os.path.dirname(__file__), "bp-tracker-nevo.py"))
bp_tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp_tracker)

def get_status():
    """Get current BP status"""
    stats = bp_tracker.get_bp_stats()
    recent = bp_tracker.get_recent_bp()
    
    if stats == "No readings yet":
        return "📊 **BP Status:** No readings recorded yet"
    
    response = f"📊 **Nevo's BP Status**\n"
    response += f"════════════════════\n"
    response += f"📈 **Total readings:** {stats['total_readings']}\n\n"
    
    response += f"**Recent Averages (last 10):**\n"
    response += f"• Systolic: {stats['recent_avg_systolic']}\n"
    response += f"• Diastolic: {stats['recent_avg_diastolic']}\n"
    response += f"• Pulse: {stats['recent_avg_pulse']}\n\n"
    
    if stats['latest']:
        latest = stats['latest']
        response += f"**Latest Reading:**\n"
        response += f"• {latest['high']}/{latest['low']} (pulse: {latest['beats']})\n"
        response += f"• {latest['date']} at {latest['time']}\n"
        if latest['notes']:
            response += f"• Notes: {latest['notes']}\n"
        response += f"\n"
    
    if len(recent) > 0:
        response += f"**Recent Readings:**\n"
        for reading in recent[-5:]:  # Last 5
            notes_txt = f" - {reading['notes']}" if reading['notes'] else ""
            response += f"• {reading['date']} {reading['time']}: {reading['high']}/{reading['low']} (pulse: {reading['beats']}){notes_txt}\n"
    
    return response

if __name__ == "__main__":
    print(get_status())