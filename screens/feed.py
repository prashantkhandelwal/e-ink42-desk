from screens.common import draw_bold_text, draw_wifi_icon, refresh_full
from xglcd_font import XglcdFont


FEED_FONT = XglcdFont("fonts/consolas.c", 6, 11)
FEED_MARGIN = 20
FEED_TOP = 52
FEED_LINE_HEIGHT = 13
FEED_ITEM_GAP = 5
FEED_BOTTOM_MARGIN = 16


def draw_text_line(image, text, x, y):
    for character in text:
        letter, width, _ = FEED_FONT.get_letter(character)
        if width == 0:
            continue
        image.blit(letter, x, y)
        x += width + 1


def wrap_headline(text, max_width):
    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if FEED_FONT.measure_text(candidate) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""

        while FEED_FONT.measure_text(word) > max_width:
            split_at = 1
            while (
                split_at < len(word)
                and FEED_FONT.measure_text(word[:split_at + 1]) <= max_width
            ):
                split_at += 1
            lines.append(word[:split_at])
            word = word[split_at:]
        current = word

    if current:
        lines.append(current)
    return lines


def show_feed(display, feed_name, headlines, feed_index, feed_count, wifi_connected, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    draw_bold_text(image, feed_name[:34], 20, 18, display.black)
    image.text("{}/{}".format(feed_index + 1, feed_count), 330, 20, display.black)
    draw_wifi_icon(display, wifi_connected)
    image.hline(20, 40, 360, display.black)

    y = FEED_TOP
    max_x = display.width - FEED_MARGIN
    max_y = display.height - FEED_BOTTOM_MARGIN
    for index, headline in enumerate(headlines[:10]):
        lines = wrap_headline(
            "{}. {}".format(index + 1, headline),
            max_x - FEED_MARGIN,
        )
        headline_height = len(lines) * FEED_LINE_HEIGHT - (
            FEED_LINE_HEIGHT - FEED_FONT.height
        )
        if y + headline_height > max_y:
            break
        for line in lines:
            draw_text_line(image, line, FEED_MARGIN, y)
            y += FEED_LINE_HEIGHT
        y += FEED_ITEM_GAP

    refresh_full(display, clear_first)