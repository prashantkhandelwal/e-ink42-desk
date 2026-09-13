from config_loader import WIFI_CONNECTED_IMAGE, WIFI_DISCONNECTED_IMAGE


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


def clean_text(text):
    text = text.replace("<![CDATA[", "").replace("]]>", "")
    replacements = (
        ("&amp;", "&"),
        ("&quot;", '"'),
        ("&apos;", "'"),
        ("&#39;", "'"),
        ("&#8216;", "'"),
        ("&#8217;", "'"),
        ("&#8220;", '"'),
        ("&#8221;", '"'),
        ("&#8230;", "..."),
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
        text = text.replace(old, new)
    text = "".join(character if 32 <= ord(character) <= 126 else " " for character in text)
    return " ".join(text.split())


def draw_scaled_text(image, text, x, y, color, scale):
    character_width = 6 * scale
    for character in text:
        rows = DIGIT_FONT[character]
        for row_index, row_bits in enumerate(rows):
            for column in range(5):
                if row_bits & (1 << (4 - column)):
                    image.fill_rect(x + column * scale, y + row_index * scale, scale, scale, color)
        x += character_width


def draw_large_text(image, text, center_x, y, color, scale=6):
    text_width = len(text) * 6 * scale - scale
    draw_scaled_text(image, text, center_x - text_width // 2, y, color, scale)


def draw_bold_text(image, text, x, y, color):
    image.text(text, x, y, color)
    image.text(text, x + 1, y, color)


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


def show_error(display, message, wifi_connected):
    image = display.image1Gray
    image.fill(display.white)
    image.text(str(message)[:45], 20, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    refresh_full(display, True)