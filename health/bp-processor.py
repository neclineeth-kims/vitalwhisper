#!/usr/bin/env python3
"""
Blood Pressure Data Processor
Converts BP tracking data to Excel format
"""

import pandas as pd
import re
from datetime import datetime

def parse_bp_entry(line):
    """Parse a BP log entry into structured data"""
    # Expected format: YYYY-MM-DD HH:MM | systolic | diastolic | pulse | notes
    parts = line.split(' | ')
    if len(parts) >= 4:
        date_time = parts[0]
        systolic = int(parts[1]) if parts[1].isdigit() else None
        diastolic = int(parts[2]) if parts[2].isdigit() else None
        pulse = int(parts[3]) if parts[3].isdigit() else None
        notes = parts[4] if len(parts) > 4 else ""
        
        return {
            'date_time': date_time,
            'date': date_time.split()[0],
            'time': date_time.split()[1],
            'systolic': systolic,
            'diastolic': diastolic, 
            'pulse': pulse,
            'notes': notes.strip()
        }
    return None

def create_excel_report(bp_data_file="health/bp-tracker.md"):
    """Convert BP tracker markdown to Excel"""
    try:
        with open(bp_data_file, 'r') as f:
            content = f.read()
        
        # Extract measurement lines (those with | separator)
        entries = []
        for line in content.split('\n'):
            if ' | ' in line and not line.startswith('#'):
                entry = parse_bp_entry(line.strip())
                if entry:
                    entries.append(entry)
        
        if not entries:
            print("No BP measurements found to export")
            return
            
        # Create DataFrame
        df = pd.DataFrame(entries)
        
        # Export to Excel
        output_file = f"health/bp-report-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"✅ BP data exported to: {output_file}")
        print(f"📊 Total measurements: {len(entries)}")
        
        return output_file
        
    except Exception as e:
        print(f"Error creating Excel report: {e}")
        return None

if __name__ == "__main__":
    create_excel_report()