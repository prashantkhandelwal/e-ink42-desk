try:
    import ujson as json
except ImportError:
    import json


with open("config.json", "r") as config_file:
    config = json.loads(config_file.read())

WIFI_SSID = config["wifi_ssid"]
WIFI_PASSWORD = config["wifi_password"]
OPENWEATHER_API_KEY = config["openweather_api_key"]

DATA_UPDATE_INTERVAL_MS = config["data_update_interval_ms"]
TIME_SYNC_INTERVAL_MS = config["time_sync_interval_ms"]
NEWS_UPDATE_INTERVAL_MS = config["news_update_interval_ms"]

QUOTE_URL = config["quote_url"]
NEWS_URL = config["news_url"]
LOCATION_URL = config["location_url"]
OPENWEATHER_URL = config["openweather_url"]
REQUEST_HEADERS = config["request_headers"]

WIFI_CONNECTED_IMAGE = config["wifi_connected_image"]
WIFI_DISCONNECTED_IMAGE = config["wifi_disconnected_image"]
KEY0_PIN = config["key0_pin"]
KEY1_PIN = config["key1_pin"]

API_PORT = config["api_port"]
API_MAX_REQUEST_BYTES = config["api_max_request_bytes"]