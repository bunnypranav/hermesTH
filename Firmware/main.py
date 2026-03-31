import time
import board
import busio
import analogio
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import adafruit_ahtx0

i2c = busio.I2C(scl=board.D5, sda=board.D4)

# OLED
displayio.release_displays()

display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

group = displayio.Group()
display.root_group = group

text = label.Label(terminalio.FONT, text="Starting", x=0, y=10)
group.append(text)

# AHT20
aht = adafruit_ahtx0.AHTx0(i2c)

# AGR10
agr = analogio.AnalogIn(board.A0)


def read_voltage(pin):
    return (pin.value * 3.3) / 65535


def voltage_to_pressure(voltage):
    V_min = 0.5
    V_max = 2.5
    P_max = 100.0

    if voltage < V_min:
        voltage = V_min
    if voltage > V_max:
        voltage = V_max

    pressure = (voltage - V_min) * (P_max / (V_max - V_min))
    return pressure


# STK8328
STK_ADDR = 0x19


def stk_write(reg, val):
    i2c.writeto(STK_ADDR, bytes([reg, val]))


def stk_read(reg, length=1):
    result = bytearray(length)
    i2c.writeto_then_readfrom(STK_ADDR, bytes([reg]), result)
    return result


try:
    stk_write(0x11, 0x00)  # power mode
    time.sleep(0.01)
except:
    print("STK init failed")


def read_accel():
    try:
        data = stk_read(0x02, 6)
        x = int.from_bytes(data[0:2], "little", signed=True)
        y = int.from_bytes(data[2:4], "little", signed=True)
        z = int.from_bytes(data[4:6], "little", signed=True)
        return x, y, z
    except:
        return 0, 0, 0


# Main loop
while True:
    try:
        # AHT20
        temp = aht.temperature
        hum = aht.relative_humidity

        # AGR10
        voltage = read_voltage(agr)
        pressure = voltage_to_pressure(voltage)

        # STK8328
        ax, ay, az = read_accel()

        # Display
        text.text = (
            f"T:{temp:.1f}C\n"
            f"H:{hum:.1f}%\n"
            f"P:{pressure:.1f} kPa"
            f"X:{ax} Y:{ay}\n"
            f"Z:{az}"
        )

    except Exception as e:
        text.text = "Error:\n" + str(e)

    time.sleep(1)
