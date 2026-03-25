from machine import I2C, Pin
from ssd1315 import SSD1315
from aht20 import AHT20
import time

# I2C setup
i2c = I2C(1, scl=Pin("PB6"), sda=Pin("PB7"), freq=400000)

# Devices
oled = SSD1315(i2c, reset_pin="PA2")
sensor = AHT20(i2c)

while True:
    temp, hum = sensor.read()

    oled.fill(0)

    if temp is not None:
        t_str = "T:{:.1f}C".format(temp)
        h_str = "H:{:.1f}%".format(hum)

        oled.text(t_str, 0, 0)
        oled.text(h_str, 0, 8)
    else:
        oled.text("Sensor Err", 0, 0)

    oled.show()

    time.sleep(1)
