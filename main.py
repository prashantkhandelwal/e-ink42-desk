import gc
from machine import Pin
import network
import ntptime
import time

from config_loader import (
    CONFIG,
    DATA_UPDATE_INTERVAL_MS,
    FEEDS,
    KEY0_PIN,
    KEY1_PIN,
    LOCATION_URL,
    NEWS_UPDATE_INTERVAL_MS,
    OPENWEATHER_API_KEY,
    OPENWEATHER_URL,
    QUOTE_URL,
    REQUEST_HEADERS,
    TIME_SYNC_INTERVAL_MS,
    WIFI_PASSWORD,
    WIFI_SSID,
    reload_feeds,
)

try:
    import urequests as requests
except ImportError:
    import requests

from epd4in2_v2 import EPD_4in2
from render_api import create_api_server, poll_render_api
from screens.common import clean_text, show_error
from screens.custom import show_custom_data
from screens.dashboard import show_dashboard
from screens.feed import show_feed


VIEW_DASHBOARD = 0
VIEW_FEED = 1
VIEW_CUSTOM = 2
ACTION_NEXT_FEED = 3
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def wifi_is_connected(wlan):
    if wlan is None:
        return False
    try:
        if wlan.isconnected():
            return True
    except OSError:
        pass
    try:
        address = wlan.ifconfig()[0]
        return bool(address and address != "0.0.0.0")
    except (OSError, IndexError):
        return False


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wifi_is_connected(wlan):
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        deadline = time.ticks_add(time.ticks_ms(), 20_000)
        while not wifi_is_connected(wlan):
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise RuntimeError("Wi-Fi connection timed out")
            time.sleep_ms(250)
    return wlan


def synchronize_clock():
    last_error = None
    for host in ("pool.ntp.org", "time.google.com"):
        try:
            ntptime.host = host
            ntptime.settime()
            print("Clock synchronized with", host)
            return
        except Exception as error:
            last_error = error
    raise RuntimeError("NTP sync failed: {}".format(last_error))


def show_time_sync_retry(display, seconds, partial=False):
    image = display.image1Gray
    countdown_text = "retrying in {} seconds".format(seconds)
    countdown_x = (display.width - len(countdown_text) * 8) // 2

    if partial:
        image.fill_rect(0, 148, display.width, 16, display.white)
        image.text(countdown_text, countdown_x, 152, display.black)
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
        return

    image.fill(display.white)
    message = "time sync failed!"
    image.text(message, (display.width - len(message) * 8) // 2, 124, display.black)
    image.text(countdown_text, countdown_x, 152, display.black)
    display.EPD_4IN2_V2_Init()
    display.EPD_4IN2_V2_Clear()
    display.EPD_4IN2_V2_Display(display.buffer_1Gray)


def synchronize_clock_with_retry(display):
    try:
        synchronize_clock()
        return False
    except Exception as error:
        print("time sync failed! retrying in 5 seconds")
        print(error)
        show_time_sync_retry(display, 5)
        for seconds in range(4, 0, -1):
            time.sleep_ms(1000)
            show_time_sync_retry(display, seconds, partial=True)
        time.sleep_ms(1000)
        synchronize_clock()
        return True


def get_stock_quote(symbol):
    response = None
    try:
        response = requests.get(QUOTE_URL.format(symbol), headers=REQUEST_HEADERS)
        if response.status_code != 200:
            raise RuntimeError("Quote API returned HTTP {}".format(response.status_code))
        result = response.json()["QuickQuoteResult"]["QuickQuote"][0]
        return {
            "price": float(result["last"]),
            "previous_close": float(result["previous_day_closing"]),
        }
    finally:
        if response is not None:
            response.close()


def get_json(url, service):
    response = None
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        if response.status_code != 200:
            raise RuntimeError("{} returned HTTP {}".format(service, response.status_code))
        return response.json()
    finally:
        if response is not None:
            response.close()


def get_feed_headlines(feed_source, limit=10):
    api_url = feed_source.get("api_url")
    if api_url:
        posts = get_json(api_url, feed_source["name"])
        headlines = []
        for post in posts[:limit]:
            title = clean_text(post.get("title", {}).get("rendered", ""))
            if title:
                headlines.append(title)
        if not headlines:
            raise RuntimeError(
                "{} contains no headlines".format(feed_source["name"])
            )
        return headlines

    response = None
    try:
        gc.collect()
        response = requests.get(feed_source["url"], headers=REQUEST_HEADERS)
        if response.status_code != 200:
            raise RuntimeError(
                "{} returned HTTP {}".format(
                    feed_source["name"], response.status_code
                )
            )

        headlines = []
        buffer = ""
        while len(headlines) < limit:
            chunk = response.raw.read(1024)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", "ignore")

            while len(headlines) < limit:
                item_start = buffer.find("<item")
                entry_start = buffer.find("<entry")
                starts = [position for position in (item_start, entry_start) if position >= 0]
                if not starts:
                    buffer = buffer[-8:]
                    break

                start = min(starts)
                if start > 0:
                    buffer = buffer[start:]
                title_start = buffer.find("<title")
                if title_start < 0:
                    break
                title_content = buffer.find(">", title_start)
                title_end = buffer.find("</title>", title_content)
                if title_content < 0 or title_end < 0:
                    break

                title = clean_text(buffer[title_content + 1:title_end])
                if title:
                    headlines.append(title)
                buffer = buffer[title_end + 8:]

        if not headlines:
            raise RuntimeError(
                "{} contains no headlines".format(feed_source["name"])
            )
        return headlines
    finally:
        if response is not None:
            response.close()


def url_encode(value):
    encoded = ""
    for byte in value.encode("utf-8"):
        if (
            48 <= byte <= 57
            or 65 <= byte <= 90
            or 97 <= byte <= 122
            or byte in (45, 46, 95, 126)
        ):
            encoded += chr(byte)
        else:
            encoded += "%{:02X}".format(byte)
    return encoded


def get_current_location():
    location_name = CONFIG.get("location_name", "")
    if location_name:
        return {"city": location_name}
    location = get_json(LOCATION_URL, "Location API")
    if not location.get("success"):
        raise RuntimeError("Location lookup failed")
    return {
        "city": location.get("city", "Current location"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
    }


def get_local_weather(location):
    if "latitude" in location:
        query = "?lat={}&lon={}&units=metric&appid={}".format(
            location["latitude"], location["longitude"], OPENWEATHER_API_KEY
        )
    else:
        query = "?q={}&units=metric&appid={}".format(
            url_encode(location["city"]), OPENWEATHER_API_KEY
        )
    current = get_json(OPENWEATHER_URL.format("weather") + query, "Weather API")
    return {
        "location": current.get("name") or location["city"],
        "timezone_offset": current["timezone"],
        "temperature": current["main"]["temp"],
        "description": current["weather"][0]["description"],
    }


def update_local_clock(weather):
    timestamp = time.time() + weather["timezone_offset"]
    local_time = time.localtime(timestamp)
    weather["clock"] = "{:02d}:{:02d}".format(local_time[3], local_time[4])
    weather["date"] = "{:02d}-{:02d}-{:04d}".format(local_time[2], local_time[1], local_time[0])
    weather["weekday"] = WEEKDAYS[local_time[6]]
    return timestamp


def wait_for_action(key_dashboard, key_feed, api_server, timeout_seconds):
    deadline = time.ticks_add(time.ticks_ms(), timeout_seconds * 1000)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if key_dashboard is not None and key_dashboard.value() == 0:
            time.sleep_ms(30)
            if key_dashboard.value() == 0:
                while key_dashboard.value() == 0:
                    time.sleep_ms(20)
                return VIEW_DASHBOARD
        if key_feed is not None and key_feed.value() == 0:
            time.sleep_ms(30)
            if key_feed.value() == 0:
                while key_feed.value() == 0:
                    time.sleep_ms(20)
                return ACTION_NEXT_FEED
        event = poll_render_api(api_server)
        if event is not None:
            return event
        time.sleep_ms(50)
    return None


def service_render_api(api_server, pending_events):
    event = poll_render_api(api_server)
    if event is not None:
        pending_events.append(event)


def main():
    display = None
    key_dashboard = None
    key_feed = None
    quote = None
    weather = None
    headlines = None
    feed_index = -1
    last_data_update = None
    last_feed_update = None
    last_time_sync = None
    current_view = VIEW_DASHBOARD
    force_render = True
    wlan = None
    api_server = None
    custom_payload = None
    pending_api_events = []

    while True:
        local_timestamp = None
        display_initialization_attempted = False
        try:
            wlan = connect_wifi()
            if api_server is None:
                api_server = create_api_server(wlan)
            service_render_api(api_server, pending_api_events)
            if key_dashboard is None:
                key_dashboard = Pin(KEY0_PIN, Pin.IN, Pin.PULL_UP)
            if key_feed is None:
                key_feed = Pin(KEY1_PIN, Pin.IN, Pin.PULL_UP)
            if display is None:
                display_initialization_attempted = True
                display = EPD_4in2()
                display.EPD_4IN2_V2_Clear()
            now = time.ticks_ms()
            time_sync_is_stale = last_time_sync is None or time.ticks_diff(now, last_time_sync) >= TIME_SYNC_INTERVAL_MS
            if time_sync_is_stale:
                try:
                    retry_was_shown = synchronize_clock_with_retry(display)
                    last_time_sync = time.ticks_ms()
                    if retry_was_shown:
                        force_render = True
                except Exception as error:
                    if last_time_sync is None:
                        raise
                    print("Clock resync failed; using RTC:", error)
                service_render_api(api_server, pending_api_events)

            data_is_stale = last_data_update is None or time.ticks_diff(now, last_data_update) >= DATA_UPDATE_INTERVAL_MS
            if current_view == VIEW_DASHBOARD and data_is_stale:
                symbol = CONFIG.get("stock_symbol", "MSFT")
                quote = get_stock_quote(symbol)
                service_render_api(api_server, pending_api_events)
                weather = get_local_weather(get_current_location())
                service_render_api(api_server, pending_api_events)
                last_data_update = time.ticks_ms()
                print("{}: {:.2f}".format(symbol, quote["price"]))

            if weather is not None:
                local_timestamp = update_local_clock(weather)
            if current_view == VIEW_DASHBOARD:
                show_dashboard(
                    display,
                    CONFIG.get("stock_symbol", "MSFT"),
                    quote,
                    weather,
                    partial=not data_is_stale and not force_render,
                    clear_first=force_render,
                )
            elif current_view == VIEW_FEED:
                feed_is_stale = last_feed_update is None or time.ticks_diff(now, last_feed_update) >= NEWS_UPDATE_INTERVAL_MS
                if feed_is_stale:
                    headlines = get_feed_headlines(FEEDS[feed_index])
                    last_feed_update = time.ticks_ms()
                if force_render or feed_is_stale:
                    show_feed(display, FEEDS[feed_index]["name"], headlines, feed_index, len(FEEDS), force_render)
            elif force_render:
                show_custom_data(display, custom_payload, force_render)
            service_render_api(api_server, pending_api_events)
            force_render = False
        except Exception as error:
            print("Update failed:", error)
            if display is None and not display_initialization_attempted:
                try:
                    display = EPD_4in2()
                    display.EPD_4IN2_V2_Clear()
                except Exception as display_error:
                    print("Display initialization failed:", display_error)
            if display is not None:
                try:
                    show_error(display, error)
                except Exception as display_error:
                    print("Error display failed:", display_error)

        gc.collect()
        if (
            display is None
            or api_server is None
            or wlan is None
            or not wifi_is_connected(wlan)
        ):
            wait_seconds = 5
        else:
            wait_seconds = 60 if local_timestamp is None else 60 - local_timestamp % 60
        requested = (
            pending_api_events.pop(0)
            if pending_api_events
            else wait_for_action(key_dashboard, key_feed, api_server, wait_seconds)
        )
        if isinstance(requested, dict):
            if requested.get("type") == "settings":
                quote = None
                weather = None
                last_data_update = None
                current_view = VIEW_DASHBOARD
                force_render = True
            elif requested.get("type") == "dashboard":
                current_view = VIEW_DASHBOARD
                force_render = True
            elif requested.get("type") == "feed":
                selected_feed_index = requested.get("feed_index", -1)
                if 0 <= selected_feed_index < len(FEEDS):
                    feed_index = selected_feed_index
                    headlines = None
                    last_feed_update = None
                    current_view = VIEW_FEED
                    force_render = True
            elif requested.get("type") == "render":
                custom_payload = requested["payload"]
                current_view = VIEW_CUSTOM
                force_render = True
        elif requested == ACTION_NEXT_FEED:
            current_feed_name = (
                FEEDS[feed_index]["name"] if 0 <= feed_index < len(FEEDS) else None
            )
            reload_feeds()
            if not FEEDS:
                raise RuntimeError("No feeds configured")
            feed_index = next(
                (
                    index
                    for index, feed in enumerate(FEEDS)
                    if feed["name"] == current_feed_name
                ),
                -1,
            )
            feed_index = (feed_index + 1) % len(FEEDS)
            headlines = None
            last_feed_update = None
            current_view = VIEW_FEED
            force_render = True
        elif requested == VIEW_DASHBOARD:
            current_view = VIEW_DASHBOARD
            force_render = True


if __name__ == "__main__":
    main()