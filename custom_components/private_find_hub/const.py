from datetime import timedelta

DOMAIN = "private_find_hub"
PLATFORMS = ("device_tracker", "sensor")
VERSION = "0.1.0-alpha.1"

CONF_ACCOUNT_LABEL = "account_label"
CONF_ADAPTER = "adapter"
CONF_VAULT_ID = "vault_id"
CONF_SELECTED_TAGS = "selected_tags"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_FRESH_MINUTES = "fresh_minutes"
CONF_AGING_MINUTES = "aging_minutes"
CONF_MAX_ACCURACY_M = "max_accuracy_m"
CONF_RECORDER_ACKNOWLEDGED = "recorder_acknowledged"

ADAPTER_MOCK = "mock"
MODE_STRICT = "strict"
DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 15
MAX_SCAN_INTERVAL_MINUTES = 360
DEFAULT_FRESH_MINUTES = 60
DEFAULT_AGING_MINUTES = 360
DEFAULT_MAX_ACCURACY_M = 1_000.0
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

RECORDER_EXAMPLE = """recorder:
  exclude:
    entity_globs:
      - \"device_tracker.private_find_hub_*\"
      - \"sensor.private_find_hub_*\""""

