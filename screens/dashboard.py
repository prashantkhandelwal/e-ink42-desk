from screens.common import (
    draw_bold_text,
    draw_large_text,
    draw_scaled_text,
    draw_wifi_icon,
    refresh_full,
)


CLOCK_X = 72
CLOCK_Y = 224
CLOCK_WIDTH = 256
CLOCK_HEIGHT = 58


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


def show_dashboard(display, symbol, quote, weather, wifi_connected, partial=False, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    change = quote["price"] - quote["previous_close"]
    percent = (change / quote["previous_close"]) * 100
    draw_bold_text(image, symbol[:10], 20, 12, display.black)
    draw_scaled_text(image, "${:.2f}".format(quote["price"]), 20, 31, display.black, 4)
    image.vline(219, 24, 48, display.black)
    draw_trend_icon(image, 235, 42, display.black, change >= 0)
    draw_bold_text(image, "{:+.2f} ({:+.2f}%)".format(change, percent), 256, 42, display.black)
    draw_wifi_icon(display, wifi_connected)
    image.hline(12, 87, 376, display.black)

    draw_location_icon(image, 20, 103, display.black)
    draw_bold_text(image, weather["location"][:22], 50, 111, display.black)
    draw_weather_icon(image, weather["description"], 17, 143, display.black)
    temperature = "{:.1f}".format(weather["temperature"])
    draw_scaled_text(image, temperature, 82, 145, display.black, 4)
    temperature_width = len(temperature) * 24 - 4
    draw_scaled_text(image, "oC", 86 + temperature_width, 147, display.black, 3)
    draw_bold_text(image, weather["description"][:19], 82, 181, display.black)

    image.vline(236, 103, 92, display.black)
    draw_calendar_icon(image, 301, 105, display.black)
    draw_scaled_text(image, weather["date"], 255, 151, display.black, 2)
    draw_bold_text(image, weather["weekday"], 318 - len(weather["weekday"]) * 4, 178, display.black)
    image.hline(12, 208, 376, display.black)

    if partial:
        image.fill_rect(CLOCK_X, CLOCK_Y, CLOCK_WIDTH, CLOCK_HEIGHT, display.white)
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
        draw_large_text(image, weather["clock"], 200, 224, display.black, 8)
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
    else:
        draw_large_text(image, weather["clock"], 200, 224, display.black, 8)
        refresh_full(display, clear_first)