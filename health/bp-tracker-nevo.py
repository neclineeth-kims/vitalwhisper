#!/usr/bin/env python3
"""
Nevo's Blood Pressure Tracker - Matches his existing Excel format
Format: No | Date | Time | Beats (Pulse) | High (Systolic) | Low (Diastolic) | Notes
"""

import pandas as pd
from datetime import datetime
import json
import os

class BPTracker:
    def __init__(self):
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(script_dir, "bp-data.json")
        self.excel_file = os.path.join(script_dir, "bp-readings.xlsx")
        self.load_data()
    
    def load_data(self):
        """Load existing BP data"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.readings = json.load(f)
        else:
            self.readings = []
    
    def save_data(self):
        """Save BP data to JSON"""
        with open(self.data_file, 'w') as f:
            json.dump(self.readings, f, indent=2)
    
    def add_reading(self, systolic, diastolic, pulse, notes="", custom_time=None):
        """Add new BP reading"""
        now = datetime.now()
        reading = {
            "no": len(self.readings) + 1,
            "date": custom_time.strftime("%Y-%m-%d") if custom_time else now.strftime("%Y-%m-%d"),
            "time": custom_time.strftime("%H:%M") if custom_time else now.strftime("%H:%M"),
            "beats": pulse,
            "high": systolic,
            "low": diastolic,
            "notes": notes,
            "timestamp": custom_time.isoformat() if custom_time else now.isoformat()
        }
        
        self.readings.append(reading)
        self.save_data()
        self.export_to_excel()
        
        return reading
    
    def export_to_excel(self):
        """Export to Excel in Nevo's format"""
        if not self.readings:
            return
        
        # Create DataFrame matching Nevo's structure
        df_data = []
        for reading in self.readings:
            df_data.append({
                "": "",  # Empty column like Nevo's
                "No": reading["no"],
                "date": reading["date"],
                "time": reading["time"], 
                "beats": reading["beats"],
                "high": reading["high"],
                "low": reading["low"],
                "notes": reading.get("notes", "")
            })
        
        df = pd.DataFrame(df_data)
        
        # Save to Excel
        with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='BP_Readings', index=False)
        
        print(f"✅ Excel updated: {self.excel_file}")
        return self.excel_file
    
    def get_recent_readings(self, days=7):
        """Get recent readings"""
        recent = []
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for reading in self.readings[-days*2:]:  # Get more than needed, filter by date
            recent.append(reading)
        
        return recent[-10:]  # Return last 10 readings
    
    def get_stats(self):
        """Get basic statistics"""
        if not self.readings:
            return "No readings yet"
        
        recent = self.readings[-10:]  # Last 10 readings
        avg_sys = sum(r["high"] for r in recent) / len(recent)
        avg_dia = sum(r["low"] for r in recent) / len(recent) 
        avg_pulse = sum(r["beats"] for r in recent) / len(recent)
        
        return {
            "total_readings": len(self.readings),
            "recent_avg_systolic": round(avg_sys, 1),
            "recent_avg_diastolic": round(avg_dia, 1),
            "recent_avg_pulse": round(avg_pulse, 1),
            "latest": self.readings[-1] if self.readings else None
        }

def parse_bp_input(text):
    """Parse BP input like '130/85/72' or '130/85/72 - morning reading'"""
    import re
    
    # Look for pattern like 130/85/72
    bp_pattern = r'(\d{2,3})/(\d{2,3})/(\d{2,3})'
    match = re.search(bp_pattern, text)
    
    if match:
        systolic = int(match.group(1))
        diastolic = int(match.group(2))
        pulse = int(match.group(3))
        
        # Extract notes (everything after the BP numbers)
        notes = re.sub(bp_pattern, '', text).strip()
        notes = re.sub(r'^[-\s]+', '', notes).strip()  # Remove leading dashes and spaces
        
        return systolic, diastolic, pulse, notes
    
    return None

# Main functions for Pedro to use
def add_bp_reading(text):
    """Add BP reading from text input"""
    tracker = BPTracker()
    parsed = parse_bp_input(text)
    
    if parsed:
        systolic, diastolic, pulse, notes = parsed
        reading = tracker.add_reading(systolic, diastolic, pulse, notes)
        
        # Get stats for response
        stats = tracker.get_stats()
        
        return {
            "success": True,
            "reading": reading,
            "stats": stats,
            "excel_file": tracker.excel_file
        }
    else:
        return {
            "success": False,
            "error": "Could not parse BP reading. Use format: 130/85/72 or 130/85/72 - notes"
        }

def get_bp_stats():
    """Get BP statistics"""
    tracker = BPTracker()
    return tracker.get_stats()

def get_recent_bp():
    """Get recent readings"""
    tracker = BPTracker()
    return tracker.get_recent_readings()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = add_bp_reading(" ".join(sys.argv[1:]))
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python bp-tracker-nevo.py '130/85/72 - morning reading'")