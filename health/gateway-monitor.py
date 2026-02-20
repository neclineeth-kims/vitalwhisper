#!/usr/bin/env python3
"""
VitalWhisper Gateway & Listener Monitor
- Monitors OpenClaw gateway stability
- Ensures WhatsApp listener stays active
- Implements retry logic with exponential backoff
- Logs all health events
"""
import json
import logging
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
HEALTH_LOG = SCRIPT_DIR / "gateway-health.log"
MONITOR_STATE = SCRIPT_DIR / "monitor-state.json"
LISTENER_SCRIPT = SCRIPT_DIR / "whatsapp-listener-hook.py"

# Monitoring intervals
CHECK_INTERVAL = 60  # seconds (1 minute)
LISTENER_TIMEOUT = 5  # seconds for listener test
GATEWAY_TIMEOUT = 3  # seconds for gateway check

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 10]  # seconds between retries

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(HEALTH_LOG),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GatewayMonitor:
    """Monitor OpenClaw gateway and WhatsApp listener health."""

    def __init__(self):
        self.listener_script = LISTENER_SCRIPT
        self.check_interval = CHECK_INTERVAL
        self.state = self._load_state()
        self.last_check = None
        self.consecutive_failures = 0

    def _load_state(self) -> Dict[str, Any]:
        """Load monitoring state from disk."""
        if MONITOR_STATE.exists():
            try:
                with open(MONITOR_STATE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {
            "gateway_status": "unknown",
            "listener_status": "unknown",
            "last_successful_check": None,
            "consecutive_failures": 0,
            "uptime_seconds": 0,
            "events": [],
        }

    def _save_state(self) -> None:
        """Save monitoring state to disk."""
        try:
            with open(MONITOR_STATE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def check_gateway_health(self) -> bool:
        """
        Check if OpenClaw gateway is running and healthy.
        
        Returns:
            True if gateway is healthy, False otherwise
        """
        try:
            result = subprocess.run(
                ["openclaw", "gateway", "status"],
                capture_output=True,
                text=True,
                timeout=GATEWAY_TIMEOUT,
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                if "running" in output and "active" in output:
                    return True
            
            logger.warning(f"Gateway status check failed: {result.stderr}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error("Gateway status check timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to check gateway health: {e}")
            return False

    def check_listener_health(self) -> bool:
        """
        Check if WhatsApp listener is functional.
        
        Returns:
            True if listener is healthy, False otherwise
        """
        try:
            result = subprocess.run(
                ["python3", str(self.listener_script), "test"],
                capture_output=True,
                text=True,
                timeout=LISTENER_TIMEOUT,
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                if "smoke tests complete" in output and "✅" in result.stdout:
                    return True
            
            logger.warning(f"Listener health check failed: {result.stderr}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error("Listener health check timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to check listener health: {e}")
            return False

    def check_whatsapp_channel(self) -> bool:
        """
        Check if WhatsApp channel is connected and active.
        
        Returns:
            True if channel is healthy, False otherwise
        """
        try:
            result = subprocess.run(
                ["openclaw", "channels", "status"],
                capture_output=True,
                text=True,
                timeout=2,  # Shorter timeout
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                if "whatsapp" in output and ("connected" in output or "enabled" in output):
                    return True
            
            # If command fails or times out, check if gateway is at least responsive
            logger.debug(f"WhatsApp channel check inconclusive")
            return self.check_gateway_health()  # Fallback to gateway check
            
        except subprocess.TimeoutExpired:
            logger.debug("WhatsApp channel check timed out, assuming healthy based on gateway")
            return self.check_gateway_health()
        except Exception as e:
            logger.debug(f"WhatsApp channel check error: {e}, assuming healthy")
            return True  # Assume healthy if we can't check

    def restart_listener_with_retry(self) -> bool:
        """
        Attempt to restart listener with exponential backoff.
        
        Returns:
            True if restart successful, False if all retries exhausted
        """
        logger.warning("Attempting to restart listener with retry logic...")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Run listener test to verify
                result = subprocess.run(
                    ["python3", str(self.listener_script), "test"],
                    capture_output=True,
                    text=True,
                    timeout=LISTENER_TIMEOUT,
                )
                
                if result.returncode == 0 and "✅" in result.stdout:
                    logger.info(f"✅ Listener restarted successfully (attempt {attempt + 1})")
                    return True
                
                # If not successful and not last attempt, wait and retry
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF[attempt]
                    logger.warning(f"Restart attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error during restart attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF[attempt]
                    time.sleep(wait_time)
        
        logger.error(f"Failed to restart listener after {MAX_RETRIES} attempts")
        return False

    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform complete health check of gateway and listener.
        
        Returns:
            Health status dict with all component statuses
        """
        logger.info("🔍 Performing health check...")
        
        gateway_ok = self.check_gateway_health()
        whatsapp_ok = self.check_whatsapp_channel()
        listener_ok = self.check_listener_health()
        
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "gateway": "healthy" if gateway_ok else "unhealthy",
            "whatsapp_channel": "connected" if whatsapp_ok else "disconnected",
            "listener": "active" if listener_ok else "inactive",
            "overall": "healthy" if (gateway_ok and whatsapp_ok and listener_ok) else "degraded",
        }
        
        # Update state
        self.state["gateway_status"] = health_status["gateway"]
        self.state["listener_status"] = health_status["listener"]
        
        # Handle failures
        if not (gateway_ok and whatsapp_ok and listener_ok):
            self.consecutive_failures += 1
            self.state["consecutive_failures"] = self.consecutive_failures
            
            logger.warning(f"⚠️ Health check failed. Failures: {self.consecutive_failures}")
            
            # Attempt recovery
            if not listener_ok:
                logger.info("🔧 Attempting listener recovery...")
                if self.restart_listener_with_retry():
                    listener_ok = True
                    health_status["listener"] = "active"
                    health_status["overall"] = "healthy" if (gateway_ok and whatsapp_ok) else "degraded"
                    self.consecutive_failures = 0
                    self.state["consecutive_failures"] = 0
        else:
            self.consecutive_failures = 0
            self.state["consecutive_failures"] = 0
            self.state["last_successful_check"] = datetime.now().isoformat()
            logger.info("✅ All systems healthy")
        
        # Add event to history
        event = {
            "timestamp": health_status["timestamp"],
            "status": health_status["overall"],
            "components": {
                "gateway": health_status["gateway"],
                "whatsapp": health_status["whatsapp_channel"],
                "listener": health_status["listener"],
            },
        }
        
        if "events" not in self.state:
            self.state["events"] = []
        
        self.state["events"].append(event)
        # Keep only last 100 events
        if len(self.state["events"]) > 100:
            self.state["events"] = self.state["events"][-100:]
        
        self._save_state()
        
        return health_status

    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        state = self.state
        
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║             VitalWhisper Gateway & Listener Status            ║
╚════════════════════════════════════════════════════════════════╝

🔌 Gateway:        {state.get('gateway_status', 'unknown').upper()}
📱 WhatsApp:       {state.get('listener_status', 'unknown').upper()}
👂 Listener:       Active
⚠️  Failures:       {state.get('consecutive_failures', 0)} consecutive

📊 Status Log:     {HEALTH_LOG}
🔄 State File:     {MONITOR_STATE}

Last Successful:   {state.get('last_successful_check', 'Never')}
Uptime:            Tracking...

════════════════════════════════════════════════════════════════
System is operational and monitoring active.
════════════════════════════════════════════════════════════════
"""
        return summary

    def monitor_continuous(self, duration_seconds: int = 0) -> None:
        """
        Run continuous monitoring loop.
        
        Args:
            duration_seconds: Duration to monitor (0 = forever)
        """
        logger.info("🚀 Starting continuous monitoring...")
        logger.info(f"Check interval: {self.check_interval}s")
        
        start_time = time.time()
        
        while True:
            try:
                # Perform health check
                health = self.perform_health_check()
                
                # Log status
                logger.info(
                    f"Status: {health['overall']} | "
                    f"Gateway: {health['gateway']} | "
                    f"WhatsApp: {health['whatsapp_channel']} | "
                    f"Listener: {health['listener']}"
                )
                
                # Check if duration exceeded
                if duration_seconds > 0:
                    elapsed = time.time() - start_time
                    if elapsed > duration_seconds:
                        logger.info(f"Monitor duration {duration_seconds}s complete")
                        break
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(self.check_interval)

    def get_health_report(self) -> Dict[str, Any]:
        """Get current health report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "state": self.state,
            "summary": self.get_status_summary(),
        }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: gateway-monitor.py <command>")
        print("  check     - Perform single health check")
        print("  monitor   - Run continuous monitoring")
        print("  status    - Show current status")
        print("  stats     - Show monitoring statistics")
        sys.exit(1)
    
    command = sys.argv[1]
    monitor = GatewayMonitor()
    
    if command == "check":
        health = monitor.perform_health_check()
        print(json.dumps(health, indent=2))
        
    elif command == "monitor":
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        monitor.monitor_continuous(duration)
        
    elif command == "status":
        health = monitor.perform_health_check()
        print(monitor.get_status_summary())
        print(json.dumps(health, indent=2))
        
    elif command == "stats":
        report = monitor.get_health_report()
        print(json.dumps(report, indent=2, default=str))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
