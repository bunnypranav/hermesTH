from machine import I2C
import time


class AHT20:
    def __init__(self, i2c, addr=0x38):
        self.i2c = i2c
        self.addr = addr
        self.init_sensor()

    def init_sensor(self):
        # Initialization command
        self.i2c.writeto(self.addr, b"\xbe\x08\x00")
        time.sleep_ms(10)

    def read(self):
        # Trigger measurement
        self.i2c.writeto(self.addr, b"\xac\x33\x00")
        time.sleep_ms(80)

        data = self.i2c.readfrom(self.addr, 6)

        if data[0] & 0x80:
            return None, None  # still busy

        # Parse humidity (20-bit)
        hum_raw = (data[1] << 12) | (data[2] << 4) | (data[3] >> 4)
        humidity = hum_raw * 100 / 1048576

        # Parse temperature (20-bit)
        temp_raw = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        temperature = temp_raw * 200 / 1048576 - 50

        return temperature, humidity
    