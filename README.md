# VitalWhisper

High-level project drop containing the automation deliverables, documentation, and tooling that power the VitalWhisper WhatsApp blood-pressure assistant.

## Repository layout

- `VITALWHISPER-EXECUTIVE-SUMMARY.md` – narrative overview with product context, positioning, and key wins.
- `VITALWHISPER-MVP-PACKAGE.md` – condensed MVP feature/package checklist for go-live readiness.
- `VITALWHISPER-PACKAGE-INDEX.md` – cross-reference of every artifact included in the delivery bundle.
- `VITALWHISPER-PACKAGE-READY.txt` – quick readiness indicator for the latest drop.
- `VITALWHISPER-QUICK-REFERENCE.md` – cheat sheet for daily operations and fast onboarding.
- `health/` – full automation stack:
  - Deployment + activation docs (`DEPLOYMENT_*.md`, `FINAL-ACTIVATION.md`, `READY_FOR_DEPLOYMENT.txt`).
  - Listener/automation code (`whatsapp-automation.py`, handler/listener hooks, monitors, scripts).
  - Testing + logs (`TEST_RESULTS.md`, `INTEGRATION_TEST_LOG.txt`, e2e scripts, `demo/`).
  - BP data utilities (`bp-*.py`, sample spreadsheets, photo/voice processors).
  - Status artifacts (`STATUS.md`, `ACTIVATION-REPORT.txt`, `SUBAGENT_COMPLETION_REPORT.md`).

## Next steps

- Clone the repo and follow `health/README.md` for local setup + diagnostics.
- Use `health/monitor.sh` to check gateway/listener health before enabling WhatsApp automation.
- Keep `VITALWHISPER-PACKAGE-READY.txt` updated when shipping new drops.
