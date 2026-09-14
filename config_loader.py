try:
    import ujson as json
except ImportError:
    import json


CONFIG_PATH = "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as config_file:
        return json.loads(config_file.read())


def save_config(updates):
    updated_config = CONFIG.copy()
    updated_config.update(updates)
    with open(CONFIG_PATH, "w") as config_file:
        config_file.write(json.dumps(updated_config))
    CONFIG.update(updates)


CONFIG = load_config()

WIFI_SSID = CONFIG["wifi_ssid"]
WIFI_PASSWORD = CONFIG["wifi_password"]
OPENWEATHER_API_KEY = CONFIG["openweather_api_key"]

DATA_UPDATE_INTERVAL_MS = CONFIG["data_update_interval_ms"]
TIME_SYNC_INTERVAL_MS = CONFIG["time_sync_interval_ms"]
NEWS_UPDATE_INTERVAL_MS = CONFIG["news_update_interval_ms"]

QUOTE_URL = CONFIG["quote_url"]
FEEDS = CONFIG["feeds"]
LOCATION_URL = CONFIG["location_url"]
OPENWEATHER_URL = CONFIG["openweather_url"]
REQUEST_HEADERS = CONFIG["request_headers"]

KEY0_PIN = CONFIG["key0_pin"]
KEY1_PIN = CONFIG["key1_pin"]

API_PORT = CONFIG["api_port"]
API_MAX_REQUEST_BYTES = CONFIG["api_max_request_bytes"]


def reload_feeds():
    latest_config = load_config()
    latest_feeds = latest_config["feeds"]
    CONFIG.update(latest_config)
    FEEDS[:] = latest_feeds