from machine import I2C, Pin
import time


class SSD1315:
    def __init__(self, i2c, addr=0x3C, reset_pin=None):
        self.i2c = i2c
        self.addr = addr
        self.width = 96
        self.height = 16
        self.pages = 2

        if reset_pin:
            self.reset = Pin(reset_pin, Pin.OUT)
        else:
            self.reset = None

        self.buffer = bytearray(self.width * self.pages)

        self.init_display()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x00, cmd]))

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b"\x40" + buf)

    def hardware_reset(self):
        if self.reset:
            self.reset.value(0)
            time.sleep_ms(10)
            self.reset.value(1)
            time.sleep_ms(10)

    def init_display(self):
        self.hardware_reset()

        self.write_cmd(0xAE)  # display off

        self.write_cmd(0xD5)
        self.write_cmd(0x80)
        self.write_cmd(0xA8)
        self.write_cmd(0x0F)  # 16 rows
        self.write_cmd(0xD3)
        self.write_cmd(0x00)
        self.write_cmd(0x40)

        self.write_cmd(0xA1)
        self.write_cmd(0xC8)

        self.write_cmd(0xDA)
        self.write_cmd(0x02)

        self.write_cmd(0x81)
        self.write_cmd(0x4F)

        self.write_cmd(0xD9)
        self.write_cmd(0x1F)
        self.write_cmd(0xDB)
        self.write_cmd(0x40)

        self.write_cmd(0xA4)
        self.write_cmd(0xA6)

        # External VCC → charge pump OFF
        self.write_cmd(0x8D)
        self.write_cmd(0x10)

        self.write_cmd(0xAF)  # display on

    def show(self):
        for page in range(self.pages):
            self.write_cmd(0xB0 + page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)

            start = page * self.width
            end = start + self.width
            self.write_data(self.buffer[start:end])

    def fill(self, color):
        val = 0xFF if color else 0x00
        for i in range(len(self.buffer)):
            self.buffer[i] = val

    def pixel(self, x, y, color):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        page = y // 8
        bit = y % 8
        index = x + page * self.width

        if color:
            self.buffer[index] |= 1 << bit
        else:
            self.buffer[index] &= ~(1 << bit)

    def text(self, string, x, y):
        font = {
            "0": [0x3E, 0x45, 0x49, 0x51, 0x3E],
            "1": [0x00, 0x21, 0x7F, 0x01, 0x00],
            "2": [0x23, 0x45, 0x49, 0x51, 0x21],
            "3": [0x42, 0x41, 0x51, 0x69, 0x46],
            "4": [0x18, 0x28, 0x48, 0x7F, 0x08],
            "5": [0x72, 0x51, 0x51, 0x51, 0x4E],
            "6": [0x1E, 0x29, 0x49, 0x49, 0x06],
            "7": [0x40, 0x47, 0x48, 0x50, 0x60],
            "8": [0x36, 0x49, 0x49, 0x49, 0x36],
            "9": [0x30, 0x49, 0x49, 0x4A, 0x3C],
            "T": [0x40, 0x40, 0x7F, 0x40, 0x40],
            "H": [0x7F, 0x08, 0x08, 0x7F, 0x00],
            "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
            "%": [0x63, 0x13, 0x08, 0x64, 0x63],
            ".": [0x00, 0x06, 0x06, 0x00, 0x00],
            ":": [0x00, 0x36, 0x36, 0x00, 0x00],
            " ": [0, 0, 0, 0, 0],
        }

        for char in string:
            if char in font:
                for col in font[char]:
                    for row in range(8):
                        self.pixel(x, y + row, (col >> row) & 1)
                    x += 1
                x += 1
