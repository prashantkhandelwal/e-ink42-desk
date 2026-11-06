from xglcd_font import XglcdFont


UI_FONT = XglcdFont("fonts/consolas.c", 6, 11)
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


def draw_text(image, text, x, y):
    for character in text:
        letter, width, _ = UI_FONT.get_letter(character)
        if width == 0:
            continue
        image.blit(letter, x, y)
        x += width + 1


def fit_text(text, max_width):
    while text and UI_FONT.measure_text(text) > max_width:
        text = text[:-1]
    return text


def draw_bold_text(image, text, x, y, color):
    image.text(text, x, y, color)
    image.text(text, x + 1, y, color)


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
    try:
        display.EPD_4IN2_V2_Init()
        display.EPD_4IN2_V2_Display(display.buffer_1Gray)
    except Exception as error:
        print("Full refresh failed; retrying after reset:", error)
        display.EPD_4IN2_V2_Init()
        display.EPD_4IN2_V2_Display(display.buffer_1Gray)


def refresh_partial(display):
    try:
        display.EPD_4IN2_V2_PartialDisplay(display.buffer_1Gray)
    except Exception as error:
        print("Partial refresh failed; recovering with full refresh:", error)
        display.EPD_4IN2_V2_Init()
        display.EPD_4IN2_V2_Display(display.buffer_1Gray)


def show_wifi_disconnected(display):
    image = display.image1Gray
    image.fill(display.white)
    center_x = display.width // 2
    center_y = display.height // 2
    origin_y = center_y + 32
    for radius in (64, 44, 24):
        inner_squared = (radius - 6) ** 2
        outer_squared = radius ** 2
        for dy in range(-radius, 1):
            for dx in range(dy, -dy + 1):
                distance_squared = dx * dx + dy * dy
                if inner_squared <= distance_squared <= outer_squared:
                    image.pixel(center_x + dx, origin_y + dy, display.black)
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            if dx * dx + dy * dy <= 36:
                image.pixel(center_x + dx, origin_y + dy, display.black)

    # A white border keeps the slash distinct where it crosses the signal arcs.
    for thickness, color in ((11, display.white), (5, display.black)):
        for step in range(97):
            x = center_x - 48 + step
            y = center_y - 40 + step * 80 // 96
            image.fill_rect(x - thickness // 2, y - thickness // 2, thickness, thickness, color)
    refresh_full(display, True)


def show_error(display, message):
    image = display.image1Gray
    image.fill(display.white)
    image.text(str(message)[:45], 20, 20, display.black)
    refresh_full(display, True)