"""Constants for Creality Cloud."""
from datetime import timedelta

DOMAIN = "creality_cloud"
CONF_TOKEN = "token"
CONF_REGION = "region"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_NOTIFY_EVENTS = "notify_events"
CONF_NOTIFY_IMAGE = "notify_image"

NOTIFY_EVENTS = ["finished", "failed", "stopped", "paused", "started", "offline", "error"]
DEFAULT_NOTIFY_EVENTS = ["finished", "failed", "error"]

SCAN_INTERVAL = timedelta(seconds=30)
HISTORY_INTERVAL = timedelta(minutes=5)
FIRMWARE_INTERVAL = timedelta(hours=6)
