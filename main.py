import gc
from machine import Pin
import network
import ntptime
import time

from config_loader import (
    DATA_UPDATE_INTERVAL_MS,
    KEY0_PIN,
    KEY1_PIN,
    LOCATION_URL,
    NEWS_UPDATE_INTERVAL_MS,
    NEWS_URL,
    OPENWEATHER_API_KEY,
    OPENWEATHER_URL,
    QUOTE_URL,
    REQUEST_HEADERS,
    TIME_SYNC_INTERVAL_MS,
    WIFI_CONNECTED_IMAGE,
    WIFI_DISCONNECTED_IMAGE,
    WIFI_PASSWORD,
    WIFI_SSID,
)

try:
    import urequests as requests
except ImportError:
    import requests

from epd4in2_v2 import EPD_4in2
from render_api import create_api_server, poll_render_api


CLOCK_X = 72
CLOCK_Y = 224
CLOCK_WIDTH = 256
CLOCK_HEIGHT = 58
VIEW_DASHBOARD = 0
VIEW_NEWS = 1
VIEW_CUSTOM = 2

DIGIT_FONT = {
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x10, 0x1E, 0x01, 0x01, 0x1E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    ":": (0x00, 0x04, 0x04, 0x00, 0x04, 0x04, 0x00),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "+": (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    "%": (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "o": (0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E, 0x00),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
}

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        deadline = time.ticks_add(time.ticks_ms(), 20_000)
        while not wlan.isconnected():
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


def get_microsoft_quote():
    response = None
    try:
        response = requests.get(QUOTE_URL, headers=REQUEST_HEADERS)
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


def get_text(url, service):
    response = None
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        if response.status_code != 200:
            raise RuntimeError("{} returned HTTP {}".format(service, response.status_code))
        return response.text
    finally:
        if response is not None:
            response.close()


def clean_news_title(title):
    title = title.replace("<![CDATA[", "").replace("]]>", "")
    replacements = (
        ("&amp;", "&"),
        ("&quot;", '"'),
        ("&apos;", "'"),
        ("&#39;", "'"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        (chr(8216), "'"),
        (chr(8217), "'"),
        (chr(8220), '"'),
        (chr(8221), '"'),
        (chr(8211), "-"),
        (chr(8212), "-"),
    )
    for old, new in replacements:
        title = title.replace(old, new)
    title = "".join(character if 32 <= ord(character) <= 126 else " " for character in title)
    return " ".join(title.split())


def get_news_headlines(limit=5):
    feed = get_text(NEWS_URL, "News feed")
    headlines = []
    position = 0

    while len(headlines) < limit:
        item_start = feed.find("<item", position)
        if item_start < 0:
            break
        title_start = feed.find("<title>", item_start)
        title_end = feed.find("</title>", title_start)
        if title_start < 0 or title_end < 0:
            break
        title = clean_news_title(feed[title_start + 7:title_end])
        if title:
            headlines.append(title)
        position = title_end + 8

    if not headlines:
        raise RuntimeError("News feed contains no headlines")
    return headlines


def get_current_location():
    location = get_json(LOCATION_URL, "Location API")
    if not location.get("success"):
        raise RuntimeError("Location lookup failed")
    return {
        "city": location.get("city", "Current location"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
    }


def get_local_weather(location):
    query = "?lat={}&lon={}&units=metric&appid={}".format(
        location["latitude"], location["longitude"], OPENWEATHER_API_KEY
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
    weather["date"] = "{:02d}-{:02d}-{:04d}".format(
        local_time[2], local_time[1], local_time[0]
    )
    weather["weekday"] = WEEKDAYS[local_time[6]]
    return timestamp


def draw_scaled_text(image, text, x, y, color, scale):
    character_width = 6 * scale

    for character in text:
        rows = DIGIT_FONT[character]
        for row_index, row_bits in enumerate(rows):
            for column in range(5):
                if row_bits & (1 << (4 - column)):
                    image.fill_rect(
                        x + column * scale,
                        y + row_index * scale,
                        scale,
                        scale,
                        color,
                    )
        x += character_width


def draw_large_text(image, text, center_x, y, color, scale=6):
    text_width = len(text) * 6 * scale - scale
    x = center_x - text_width // 2
    draw_scaled_text(image, text, x, y, color, scale)


def draw_bold_text(image, text, x, y, color):
    image.text(text, x, y, color)
    image.text(text, x + 1, y, color)


def draw_location_icon(image, x, y, color):
    image.fill_rect(x + 5, y, 8, 2, color)
    image.fill_rect(x + 2, y + 2, 14, 10, color)
    image.fill_rect(x + 4, y + 12, 10, 4, color)
    image.fill_rect(x + 6, y + 16, 6, 4, color)
    image.fill_rect(x + 8, y + 20, 2, 3, color)
    image.fill_rect(x + 6, y + 4, 6, 6, 0xFF)


def draw_weather_icon(image, description, x, y, color):
    image.fill_rect(x + 8, y + 14, 42, 18, color)
    image.fill_rect(x + 14, y + 8, 28, 24, color)
    image.fill_rect(x + 20, y + 3, 16, 29, color)
    if "rain" in description.lower() or "drizzle" in description.lower():
        image.fill_rect(x + 14, y + 38, 4, 9, color)
        image.fill_rect(x + 29, y + 35, 4, 9, color)
        image.fill_rect(x + 42, y + 39, 4, 9, color)


def draw_calendar_icon(image, x, y, color):
    image.rect(x, y + 5, 34, 30, color)
    image.fill_rect(x, y + 5, 34, 8, color)
    image.fill_rect(x + 7, y, 4, 9, color)
    image.fill_rect(x + 23, y, 4, 9, color)
    for row in range(2):
        for column in range(3):
            image.fill_rect(x + 7 + column * 8, y + 17 + row * 7, 4, 3, color)


def draw_trend_icon(image, x, y, color, positive):
    if positive:
        for row in range(8):
            image.hline(x + 8 - row, y + row, row * 2 + 1, color)
    else:
        for row in range(8):
            image.hline(x + row, y + row, 15 - row * 2, color)


def draw_wifi_icon(display, connected):
    image_file = WIFI_CONNECTED_IMAGE if connected else WIFI_DISCONNECTED_IMAGE
    try:
        display.draw_bmp_img(image_file, 368, 6)
    except (OSError, ValueError) as error:
        print("Wi-Fi icon failed:", error)


def wrap_text(text, width=44, max_lines=3):
    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:width]
            if len(lines) == max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines


def refresh_full(display, clear_first=False):
    display.EPD_4IN2_V2_Init()
    if clear_first:
        display.EPD_4IN2_V2_Clear()
    display.EPD_4IN2_V2_Display(display.buffer_1Gray)


def show_dashboard(
    display, quote, weather, wifi_connected, partial=False, clear_first=False
):
    image = display.image1Gray
    image.fill(display.white)
    change = quote["price"] - quote["previous_close"]
    percent = (change / quote["previous_close"]) * 100
    draw_bold_text(image, "MSFT", 20, 12, display.black)
    draw_scaled_text(
        image, "${:.2f}".format(quote["price"]), 20, 31, display.black, 4
    )
    image.vline(219, 24, 48, display.black)
    draw_trend_icon(image, 235, 42, display.black, change >= 0)
    draw_bold_text(
        image,
        "{:+.2f} ({:+.2f}%)".format(change, percent),
        256,
        42,
        display.black,
    )
    draw_wifi_icon(display, wifi_connected)
    image.hline(12, 87, 376, display.black)

    draw_location_icon(image, 20, 103, display.black)
    draw_bold_text(image, weather["location"][:22], 50, 111, display.black)
    draw_weather_icon(image, weather["description"], 17, 143, display.black)
    temperature = "{:.1f}".format(weather["temperature"])
    draw_scaled_text(image, temperature, 82, 145, display.black, 4)
    temperature_width = len(temperature) * 24 - 4
    draw_scaled_text(
        image, "oC", 86 + temperature_width, 147, display.black, 3
    )
    draw_bold_text(image, weather["description"][:19], 82, 181, display.black)

    image.vline(236, 103, 92, display.black)
    draw_calendar_icon(image, 301, 105, display.black)
    draw_scaled_text(image, weather["date"], 255, 151, display.black, 2)
    weekday_x = 318 - len(weather["weekday"]) * 4
    draw_bold_text(image, weather["weekday"], weekday_x, 178, display.black)
    image.hline(12, 208, 376, display.black)

    if partial:
        image.fill_rect(
            CLOCK_X, CLOCK_Y, CLOCK_WIDTH, CLOCK_HEIGHT, display.white
        )
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
        draw_large_text(image, weather["clock"], 200, 224, display.black, 8)
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
    else:
        draw_large_text(image, weather["clock"], 200, 224, display.black, 8)
        refresh_full(display, clear_first)

def show_news(display, headlines, wifi_connected, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    image.text("BBC NEWS", 20, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    image.hline(20, 40, 360, display.black)

    y = 54
    for index, headline in enumerate(headlines):
        lines = wrap_text("{}. {}".format(index + 1, headline))
        for line in lines:
            image.text(line, 20, y, display.black)
            y += 11
        y += 8

    refresh_full(display, clear_first)


def show_custom_data(display, payload, wifi_connected, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    title = clean_news_title(str(payload.get("title", "MICROPYTHON DATA")))[:36]
    draw_bold_text(image, title, 20, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    image.hline(20, 40, 360, display.black)

    lines = payload.get("lines")
    if lines is None:
        data = payload.get("data", {})
        lines = ["{}: {}".format(key, value) for key, value in data.items()]

    y = 56
    for value in lines:
        text = clean_news_title(str(value))
        for line in wrap_text(text, width=44, max_lines=2):
            image.text(line, 20, y, display.black)
            y += 12
        y += 6
        if y > 282:
            break

    refresh_full(display, clear_first)


def show_error(display, message, wifi_connected):
    image = display.image1Gray
    image.fill(display.white)
    image.text(str(message)[:45], 20, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    refresh_full(display, True)


def wait_for_view(key_dashboard, key_news, api_server, timeout_seconds):
    deadline = time.ticks_add(time.ticks_ms(), timeout_seconds * 1000)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if key_dashboard.value() == 0:
            time.sleep_ms(30)
            if key_dashboard.value() == 0:
                while key_dashboard.value() == 0:
                    time.sleep_ms(20)
                return VIEW_DASHBOARD
        if key_news.value() == 0:
            time.sleep_ms(30)
            if key_news.value() == 0:
                while key_news.value() == 0:
                    time.sleep_ms(20)
                return VIEW_NEWS
        payload = poll_render_api(api_server)
        if payload is not None:
            return VIEW_CUSTOM, payload
        time.sleep_ms(50)
    return None


def main():
    display = EPD_4in2()
    key_dashboard = Pin(KEY0_PIN, Pin.IN, Pin.PULL_UP)
    key_news = Pin(KEY1_PIN, Pin.IN, Pin.PULL_UP)
    quote = None
    weather = None
    headlines = None
    last_data_update = None
    last_news_update = None
    last_time_sync = None
    last_wifi_connected = None
    current_view = VIEW_DASHBOARD
    force_render = True
    wlan = None
    api_server = None
    custom_payload = None

    while True:
        try:
            wlan = connect_wifi()
            if api_server is None:
                api_server = create_api_server(wlan)
            now = time.ticks_ms()
            time_sync_is_stale = (
                last_time_sync is None
                or time.ticks_diff(now, last_time_sync) >= TIME_SYNC_INTERVAL_MS
            )
            if time_sync_is_stale:
                try:
                    synchronize_clock()
                    last_time_sync = time.ticks_ms()
                except Exception as error:
                    if last_time_sync is None:
                        raise
                    print("Clock resync failed; using RTC:", error)

            data_is_stale = (
                last_data_update is None
                or time.ticks_diff(now, last_data_update) >= DATA_UPDATE_INTERVAL_MS
            )
            if data_is_stale:
                quote = get_microsoft_quote()
                location = get_current_location()
                weather = get_local_weather(location)
                last_data_update = time.ticks_ms()
                print("MSFT: {:.2f}".format(quote["price"]))

            local_timestamp = update_local_clock(weather)
            wifi_connected = wlan.isconnected()
            wifi_state_changed = (
                last_wifi_connected is not None
                and wifi_connected != last_wifi_connected
            )
            if current_view == VIEW_DASHBOARD:
                show_dashboard(
                    display,
                    quote,
                    weather,
                    wifi_connected=wifi_connected,
                    partial=(
                        not data_is_stale
                        and not wifi_state_changed
                        and not force_render
                    ),
                    clear_first=force_render,
                )
            elif current_view == VIEW_NEWS:
                news_is_stale = (
                    last_news_update is None
                    or time.ticks_diff(now, last_news_update) >= NEWS_UPDATE_INTERVAL_MS
                )
                if news_is_stale:
                    headlines = get_news_headlines()
                    last_news_update = time.ticks_ms()
                if force_render or news_is_stale or wifi_state_changed:
                    show_news(
                        display,
                        headlines,
                        wifi_connected,
                        clear_first=force_render,
                    )
            else:
                if force_render or wifi_state_changed:
                    show_custom_data(
                        display,
                        custom_payload,
                        wifi_connected,
                        clear_first=force_render,
                    )

            last_wifi_connected = wifi_connected
            force_render = False
        except Exception as error:
            print("Update failed:", error)
            wifi_connected = wlan is not None and wlan.isconnected()
            show_error(display, error, wifi_connected)
            last_wifi_connected = wifi_connected
            local_timestamp = None

        gc.collect()
        wait_seconds = 60 if local_timestamp is None else 60 - local_timestamp % 60
        requested = wait_for_view(
            key_dashboard, key_news, api_server, wait_seconds
        )
        if isinstance(requested, tuple):
            current_view, custom_payload = requested
            force_render = True
        elif requested is not None and requested != current_view:
            current_view = requested
            force_render = True


if __name__ == "__main__":
    main()

