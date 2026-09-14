from machine import Pin, SPI
import bmp_file_reader as bmpr
import framebuf
import utime


EPD_WIDTH = 400
EPD_HEIGHT = 300

SCK_PIN = 10
DIN_PIN = 11
RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13

LUT_ALL = [
    0x01, 0x0A, 0x1B, 0x0F, 0x03, 0x01, 0x01,
    0x05, 0x0A, 0x01, 0x0A, 0x01, 0x01, 0x01,
    0x05, 0x08, 0x03, 0x02, 0x04, 0x01, 0x01,
    0x01, 0x04, 0x04, 0x02, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x0A, 0x1B, 0x0F, 0x03, 0x01, 0x01,
    0x05, 0x4A, 0x01, 0x8A, 0x01, 0x01, 0x01,
    0x05, 0x48, 0x03, 0x82, 0x84, 0x01, 0x01,
    0x01, 0x84, 0x84, 0x82, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x0A, 0x1B, 0x8F, 0x03, 0x01, 0x01,
    0x05, 0x4A, 0x01, 0x8A, 0x01, 0x01, 0x01,
    0x05, 0x48, 0x83, 0x82, 0x04, 0x01, 0x01,
    0x01, 0x04, 0x04, 0x02, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x8A, 0x1B, 0x8F, 0x03, 0x01, 0x01,
    0x05, 0x4A, 0x01, 0x8A, 0x01, 0x01, 0x01,
    0x05, 0x48, 0x83, 0x02, 0x04, 0x01, 0x01,
    0x01, 0x04, 0x04, 0x02, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x8A, 0x9B, 0x8F, 0x03, 0x01, 0x01,
    0x05, 0x4A, 0x01, 0x8A, 0x01, 0x01, 0x01,
    0x05, 0x48, 0x03, 0x42, 0x04, 0x01, 0x01,
    0x01, 0x04, 0x04, 0x42, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x02, 0x00, 0x00, 0x07, 0x17, 0x41, 0xA8,
    0x32, 0x30,
]


class EPD_4in2:
    def __init__(self):
        self.reset_pin = Pin(RST_PIN, Pin.OUT, value=1)
        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT, value=1)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.Seconds_1_5S = 0
        self.Seconds_1S = 1
        self.LUT_ALL = LUT_ALL
        self.black = 0x00
        self.white = 0xFF
        self.darkgray = 0xAA
        self.grayish = 0x55

        utime.sleep_ms(1000)
        self.spi = SPI(
            1,
            baudrate=4_000_000,
            sck=Pin(SCK_PIN),
            mosi=Pin(DIN_PIN),
        )
        self.dc_pin = Pin(DC_PIN, Pin.OUT, value=0)

        self.buffer_1Gray = bytearray(self.height * self.width // 8)
        self.image1Gray = framebuf.FrameBuffer(
            self.buffer_1Gray, self.width, self.height, framebuf.MONO_HLSB
        )

        self.EPD_4IN2_V2_Init()
        utime.sleep_ms(500)

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(10)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200)

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def send_data1(self, buffer):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi.write(bytearray(buffer))
        self.digital_write(self.cs_pin, 1)

    def ReadBusy(self, timeout_ms=15_000):
        print("e-Paper busy")
        deadline = utime.ticks_add(utime.ticks_ms(), timeout_ms)
        while self.digital_read(self.busy_pin) == 1:
            if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
                raise RuntimeError("e-Paper busy timed out")
            self.delay_ms(100)
        print("e-Paper busy release")

    def _turn_on_display(self, control):
        self.send_command(0x22)
        self.send_data(control)
        self.send_command(0x20)
        self.ReadBusy()

    def TurnOnDisplay(self):
        self._turn_on_display(0xF7)

    def TurnOnDisplay_Fast(self):
        self._turn_on_display(0xC7)

    def TurnOnDisplay_Partial(self):
        self._turn_on_display(0xFF)

    def TurnOnDisplay_4GRAY(self):
        self._turn_on_display(0xCF)

    def _set_ram_area(self):
        self.send_command(0x11)
        self.send_data(0x03)
        self.send_command(0x44)
        self.send_data(0x00)
        self.send_data(0x31)
        self.send_command(0x45)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data(0x2B)
        self.send_data(0x01)
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)
        self.ReadBusy()

    def EPD_4IN2_V2_Init(self):
        self.reset()
        self.ReadBusy()
        self.send_command(0x12)
        self.ReadBusy()
        self.send_command(0x21)
        self.send_data(0x40)
        self.send_data(0x00)
        self.send_command(0x3C)
        self.send_data(0x05)
        self._set_ram_area()

    def EPD_4IN2_V2_Init_Fast(self, mode):
        self.reset()
        self.ReadBusy()
        self.send_command(0x12)
        self.ReadBusy()
        self.send_command(0x21)
        self.send_data(0x40)
        self.send_data(0x00)
        self.send_command(0x3C)
        self.send_data(0x05)
        self.send_command(0x1A)
        self.send_data(0x6E if mode == self.Seconds_1_5S else 0x5A)
        self.send_command(0x22)
        self.send_data(0x91)
        self.send_command(0x20)
        self.ReadBusy()
        self._set_ram_area()

    def Lut(self):
        self.send_command(0x32)
        for value in self.LUT_ALL[:227]:
            self.send_data(value)
        self.send_command(0x3F)
        self.send_data(self.LUT_ALL[227])
        self.send_command(0x03)
        self.send_data(self.LUT_ALL[228])
        self.send_command(0x04)
        self.send_data(self.LUT_ALL[229])
        self.send_data(self.LUT_ALL[230])
        self.send_data(self.LUT_ALL[231])
        self.send_command(0x2C)
        self.send_data(self.LUT_ALL[232])

    def EPD_4IN2_V2_Init_4Gray(self):
        self.reset()
        self.ReadBusy()
        self.send_command(0x12)
        self.ReadBusy()
        self.send_command(0x21)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x3C)
        self.send_data(0x03)
        self.send_command(0x0C)
        for value in (0x8B, 0x9C, 0xA4, 0x0F):
            self.send_data(value)
        self.Lut()
        self._set_ram_area()

    def EPD_4IN2_V2_Clear(self):
        self.image1Gray.fill(self.white)
        for command in (0x24, 0x26):
            self.send_command(command)
            self.send_data1(self.buffer_1Gray)
        self.TurnOnDisplay()

    def EPD_4IN2_V2_Display(self, image):
        for command in (0x24, 0x26):
            self.send_command(command)
            self.send_data1(image)
        self.TurnOnDisplay()

    def EPD_4IN2_V2_Display_Fast(self, image):
        for command in (0x24, 0x26):
            self.send_command(command)
            self.send_data1(image)
        self.TurnOnDisplay_Fast()

    def EPD_4IN2_V2_PartialDisplay(self, image):
        self.send_command(0x3C)
        self.send_data(0x80)
        self.send_command(0x21)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x3C)
        self.send_data(0x80)
        self._set_ram_area()
        self.send_command(0x24)
        self.send_data1(image)
        self.TurnOnDisplay_Partial()
        self._set_ram_area()
        self.send_command(0x26)
        self.send_data1(image)

    def _send_gray_plane(self, image, gray1_bit, gray2_bit):
        for index in range(15000):
            output = 0
            for byte_index in range(2):
                value = image[index * 2 + byte_index]
                for pixel_index in range(4):
                    pixel = value & 0x03
                    if pixel == 0x03:
                        output |= 0x01
                    elif pixel == 0x02:
                        output |= gray1_bit
                    elif pixel == 0x01:
                        output |= gray2_bit
                    if byte_index != 1 or pixel_index != 3:
                        output <<= 1
                    value >>= 2
            self.send_data(output)

    def EPD_4IN2_V2_4GrayDisplay(self, image):
        self.send_command(0x24)
        self._send_gray_plane(image, 1, 0)
        self.send_command(0x26)
        self._send_gray_plane(image, 0, 1)
        self.TurnOnDisplay_4GRAY()

    def Sleep(self):
        self.send_command(0x10)
        self.send_data(0x01)

            
    
    def draw_mono_img(self, img_file, x, y, width=32, height=32):
        """Draw a monochrome image from a file at the given x, y coordinates.
        The file should contain comma-separated binary literals (e.g. 0b10001001, 0b01101010, ...)
        as produced by img2bin.py. Each byte represents 8 horizontal pixels.
        """
        with open(img_file, 'r') as f:
            content = f.read()
        # Parse the comma-separated binary string values into byte integers
        tokens = [t.strip() for t in content.split(',') if t.strip()]
        img_bytes = [int(t, 2) for t in tokens]
        # Draw pixel by pixel onto the framebuffer at (x, y)
        bytes_per_row = width // 8
        for row in range(height):
            for col_byte in range(bytes_per_row):
                idx = row * bytes_per_row + col_byte
                if idx >= len(img_bytes):
                    return
                byte = img_bytes[idx]
                for bit in range(8):
                    pixel_on = (byte >> (7 - bit)) & 1
                    color = 0x00 if pixel_on else 0xff
                    self.image1Gray.pixel(x + col_byte * 8 + bit, y + row, color)
    
    
    def draw_bmp_img(self, img_file, x_offset, y_offset):
        """Draw a Bitmap (BMP) image from the file.
        """
        with open(img_file, "rb") as file:
            reader = bmpr.BMPFileReader(file)
            rows = [reader.get_row(row_i) for row_i in range(reader.get_height())]
            use_alpha = any(color.alpha != 0 for row in rows for color in row)

            for row_i, row in enumerate(rows):
                for col_i, color in enumerate(row):
                    alpha = color.alpha if use_alpha else 255
                    brightness = (
                        (color.red + color.green + color.blue) * alpha
                        + 765 * (255 - alpha)
                    ) // 255
                    bw = 0x00 if brightness < 384 else 0xff
                    self.image1Gray.pixel(x_offset + col_i, y_offset + row_i, bw)
        
    
    def draw_qr(self, matrix, x_offset=5, y_offset=50, scale=3):
        for y, row in enumerate(matrix):
            for x, val in enumerate(row):
                color = 0x00 if val else 0xff  # black or white
                for dy in range(scale):
                    for dx in range(scale):
                        self.image1Gray.pixel(
                            x_offset + x * scale + dx,
                            y_offset + y * scale + dy,
                            color,
                        )

    def draw_icon(self, icon_bytes, x_offset=0, y_offset=0, width=16, height=16):
        bytes_per_row = width // 8
        for y in range(height):
            for byte_index in range(bytes_per_row):
                i = y * bytes_per_row + byte_index
                byte = icon_bytes[i]
                # If MicroPython returns a string, convert to int
                if isinstance(byte, str):
                    byte = ord(byte)
                for bit in range(8):
                    pixel_on = (byte >> (7 - bit)) & 0x01
                    color = 0x00 if pixel_on else 0xff
                    x = x_offset + byte_index * 8 + bit
                    self.image1Gray.pixel(x, y_offset + y, color)