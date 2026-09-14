from screens.common import UI_FONT, draw_bold_text, draw_text, fit_text, refresh_full


FEED_MARGIN = 20
FEED_TOP = 54
FEED_LINE_HEIGHT = 19
FEED_ITEM_GAP = 5
FEED_BOTTOM_MARGIN = 16


def draw_text_line(image, text, x, y):
    draw_text(image, text, x, y)


def wrap_headline(text, max_width):
    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if UI_FONT.measure_text(candidate) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""

        while UI_FONT.measure_text(word) > max_width:
            split_at = 1
            while (
                split_at < len(word)
                and UI_FONT.measure_text(word[:split_at + 1]) <= max_width
            ):
                split_at += 1
            lines.append(word[:split_at])
            word = word[split_at:]
        current = word

    if current:
        lines.append(current)
    return lines


def show_feed(display, feed_name, headlines, feed_index, feed_count, clear_first=False):
    image = display.image1Gray
    image.fill(display.white)
    draw_bold_text(image, fit_text(feed_name, 290), 20, 14, display.black)
    draw_text(image, "{}/{}".format(feed_index + 1, feed_count), 330, 20)
    image.hline(20, 44, 360, display.black)

    y = FEED_TOP
    max_x = display.width - FEED_MARGIN
    max_y = display.height - FEED_BOTTOM_MARGIN
    for index, headline in enumerate(headlines[:10]):
        lines = wrap_headline(
            "{}. {}".format(index + 1, headline),
            max_x - FEED_MARGIN,
        )
        headline_height = len(lines) * FEED_LINE_HEIGHT - (
            FEED_LINE_HEIGHT - UI_FONT.height
        )
        if y + headline_height > max_y:
            break
        for line in lines:
            draw_text_line(image, line, FEED_MARGIN, y)
            y += FEED_LINE_HEIGHT
        y += FEED_ITEM_GAP

    refresh_full(display, clear_first)