import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


with patch.dict(sys.modules, {"xglcd_font": SimpleNamespace(XglcdFont=Mock())}):
    common = importlib.import_module("screens.common")


class Image:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = {}
        self.text_calls = []

    def fill(self, color):
        self.background = color
        self.pixels.clear()

    def pixel(self, x, y, color):
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise AssertionError("Pixel outside display")
        self.pixels[x, y] = color

    def fill_rect(self, x, y, width, height, color):
        for row in range(y, y + height):
            for column in range(x, x + width):
                self.pixel(column, row, color)

    def text(self, text, x, y, color):
        self.text_calls.append((text, x, y, color))


def make_display(width=400, height=300):
    return SimpleNamespace(
        width=width,
        height=height,
        white=0xFF,
        black=0,
        image1Gray=Image(width, height),
        buffer_1Gray=bytearray(width * height // 8),
        EPD_4IN2_V2_Init=Mock(),
        EPD_4IN2_V2_Display=Mock(),
    )


class WifiDisconnectedTests(unittest.TestCase):
    def test_centered_icon_with_arcs_dot_and_diagonal_without_text(self):
        for width, height in ((400, 300), (300, 400)):
            with self.subTest(width=width, height=height):
                display = make_display(width, height)
                image = display.image1Gray
                image.pixel(0, 0, display.black)
                common.show_wifi_disconnected(display)
                cx, cy = width // 2, height // 2
                self.assertEqual(image.background, display.white)
                self.assertNotIn((0, 0), image.pixels)
                self.assertEqual(image.text_calls, [])
                for point in ((cx, cy - 30), (cx, cy - 12), (cx - 12, cy + 12), (cx, cy + 32)):
                    self.assertEqual(image.pixels[point], display.black)
                for step in range(97):
                    point = (cx - 48 + step, cy - 40 + step * 80 // 96)
                    self.assertEqual(image.pixels[point], display.black)
                black_pixels = [point for point, color in image.pixels.items() if color == display.black]
                self.assertEqual(min(x for x, _ in black_pixels) + max(x for x, _ in black_pixels), 2 * cx)
                self.assertEqual(min(y for _, y in black_pixels) + max(y for _, y in black_pixels), 2 * cy)
                display.EPD_4IN2_V2_Init.assert_called_once_with()
                display.EPD_4IN2_V2_Display.assert_called_once_with(display.buffer_1Gray)

    def test_other_errors_keep_the_existing_message(self):
        display = make_display()
        common.show_error(display, RuntimeError("NTP sync failed"))
        self.assertEqual(display.image1Gray.text_calls, [("NTP sync failed", 20, 20, display.black)])
        display.EPD_4IN2_V2_Display.assert_called_once_with(display.buffer_1Gray)


if __name__ == "__main__":
    unittest.main()
