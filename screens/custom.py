from screens.common import clean_text, draw_bold_text, draw_wifi_icon, refresh_full, wrap_text


def show_custom_data(display, payload, wifi_connected, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    title = clean_text(str(payload.get("title", "MICROPYTHON DATA")))[:36]
    draw_bold_text(image, title, 20, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    image.hline(20, 40, 360, display.black)

    lines = payload.get("lines")
    if lines is None:
        data = payload.get("data", {})
        lines = ["{}: {}".format(key, value) for key, value in data.items()]

    y = 56
    for value in lines:
        for line in wrap_text(clean_text(str(value)), width=44, max_lines=2):
            image.text(line, 20, y, display.black)
            y += 12
        y += 6
        if y > 282:
            break

    refresh_full(display, clear_first)