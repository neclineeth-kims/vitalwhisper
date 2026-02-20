#!/bin/bash
# VitalWhisper Gateway & Listener Health Monitor
# Fast, reliable monitoring without subprocess overhead

set -e

HEALTH_DIR="/home/raindrop/.openclaw/workspace/health"
LISTENER_LOG="$HEALTH_DIR/listener-events.log"
HEALTH_REPORT="$HEALTH_DIR/monitor-health.json"
LISTENER_HOOK="$HEALTH_DIR/whatsapp-listener-hook.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if listener is receiving messages
check_listener_recent_activity() {
    if [ ! -f "$LISTENER_LOG" ]; then
        echo "0"
        return
    fi
    
    # Count messages in last 5 minutes
    TIMESTAMP=$(($(date +%s) - 300))
    RECENT=$(tail -20 "$LISTENER_LOG" 2>/dev/null | grep -c "timestamp" || echo "0")
    
    if [ "$RECENT" -gt 0 ]; then
        echo "1"
    else
        echo "0"
    fi
}

# Function to check gateway status
check_gateway() {
    if timeout 2 openclaw gateway status 2>&1 | grep -q "running"; then
        echo "1"
    else
        echo "0"
    fi
}

# Function to check listener file exists and is executable
check_listener_available() {
    if [ -x "$LISTENER_HOOK" ]; then
        echo "1"
    else
        echo "0"
    fi
}

# Function to get latest BP data
get_latest_reading() {
    if [ -f "$HEALTH_DIR/bp-data.json" ]; then
        tail -1 "$HEALTH_DIR/bp-data.json" 2>/dev/null | grep -o '"no":[0-9]*' | cut -d':' -f2 || echo "unknown"
    else
        echo "unknown"
    fi
}

# Function to generate health report
generate_report() {
    GATEWAY=$(check_gateway)
    LISTENER=$(check_listener_available)
    ACTIVITY=$(check_listener_recent_activity)
    LATEST=$(get_latest_reading)
    TIMESTAMP=$(date -Iseconds)
    
    # Determine overall status
    if [ "$GATEWAY" = "1" ] && [ "$LISTENER" = "1" ]; then
        OVERALL="healthy"
    else
        OVERALL="degraded"
    fi
    
    cat > "$HEALTH_REPORT" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "overall_status": "$OVERALL",
  "components": {
    "gateway": {
      "status": $([ "$GATEWAY" = "1" ] && echo '"running"' || echo '"stopped"'),
      "check_passed": $([ "$GATEWAY" = "1" ] && echo 'true' || echo 'false')
    },
    "listener": {
      "status": $([ "$LISTENER" = "1" ] && echo '"available"' || echo '"missing"'),
      "check_passed": $([ "$LISTENER" = "1" ] && echo 'true' || echo 'false'),
      "recent_activity": $([ "$ACTIVITY" = "1" ] && echo 'true' || echo 'false')
    },
    "bp_data": {
      "latest_reading_no": "$LATEST"
    }
  }
}
EOF
    
    # Print report
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   VitalWhisper System Health Monitor${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Timestamp:           $TIMESTAMP"
    echo "Overall Status:      $([ "$OVERALL" = "healthy" ] && echo -e "${GREEN}$OVERALL${NC}" || echo -e "${YELLOW}$OVERALL${NC}")"
    echo ""
    echo "Gateway:             $([ "$GATEWAY" = "1" ] && echo -e "${GREEN}✓ Running${NC}" || echo -e "${RED}✗ Stopped${NC}")"
    echo "Listener:            $([ "$LISTENER" = "1" ] && echo -e "${GREEN}✓ Available${NC}" || echo -e "${RED}✗ Missing${NC}")"
    echo "Recent Activity:     $([ "$ACTIVITY" = "1" ] && echo -e "${GREEN}✓ Yes${NC}" || echo -e "${YELLOW}✗ No${NC}")"
    echo "Latest BP Reading:   #$LATEST"
    echo ""
    echo "Report saved to:     $HEALTH_REPORT"
    echo ""
}

# Function to monitor continuously
monitor_continuous() {
    INTERVAL=${1:-60}
    echo "Starting continuous monitoring (interval: ${INTERVAL}s)"
    echo "Press Ctrl+C to stop"
    echo ""
    
    while true; do
        generate_report
        sleep "$INTERVAL"
    done
}

# Main commands
case "${1:-status}" in
    status)
        generate_report
        ;;
    monitor)
        INTERVAL=${2:-60}
        monitor_continuous "$INTERVAL"
        ;;
    check)
        # Quick JSON output
        GATEWAY=$(check_gateway)
        LISTENER=$(check_listener_available)
        echo "{\"gateway\": $GATEWAY, \"listener\": $LISTENER}"
        ;;
    *)
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  status              Show current system status"
        echo "  monitor [interval]  Continuous monitoring (default 60s)"
        echo "  check               Quick health check (JSON)"
        echo ""
        exit 1
        ;;
esac
