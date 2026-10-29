"""Monitor feature configuration from environment."""
import os

IDLE_THRESHOLD_SECONDS = int(os.getenv("MONITOR_IDLE_THRESHOLD_SECONDS", "30"))
HEARTBEAT_STALE_SECONDS = int(os.getenv("MONITOR_HEARTBEAT_STALE_SECONDS", "120"))
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("MONITOR_HEARTBEAT_INTERVAL_SECONDS", "45"))

# Pairing desktop agent ↔ web account
PAIRING_CODE_TTL_MINUTES = int(os.getenv("MONITOR_PAIRING_TTL_MINUTES", "30"))
PAIRING_CODE_GRACE_SECONDS = int(os.getenv("MONITOR_PAIRING_GRACE_SECONDS", "120"))

# All login roles that may pair the desktop agent and appear in analytics
TRACKED_USER_ROLES = frozenset(
    {"superadmin", "admin", "scrum", "team_leader", "worker"}
)
