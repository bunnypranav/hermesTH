import time
import struct
import framebuf
from machine import I2C, Pin

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400_000)


def i2c_write(addr, data):
    i2c.writeto(addr, data)


def i2c_read(addr, n):
    return i2c.readfrom(addr, n)


def i2c_write_reg(addr, reg, val):
    i2c.writeto(addr, bytes([reg, val]))


def i2c_read_reg(addr, reg, n):
    i2c.writeto(addr, bytes([reg]))
    return i2c.readfrom(addr, n)


# STK8328-C
STK_ADDR = 0x1F
STK_REG_CHIP_ID = 0x00
STK_REG_XOUT1 = 0x02
STK_REG_RANGESEL = 0x0F
STK_REG_BWSEL = 0x10
STK_REG_POWMODE = 0x11
STK_REG_SWRST = 0x14

STK_RANGE_2G = 0x03
STK_RANGE_4G = 0x05
STK_RANGE_8G = 0x08
STK_RANGE_16G = 0x0C
STK_BW_125HZ = 0x0C

_STK_SENSITIVITY = {
    STK_RANGE_2G: 16384.0,
    STK_RANGE_4G: 8192.0,
    STK_RANGE_8G: 4096.0,
    STK_RANGE_16G: 2048.0,
}
_stk_range = STK_RANGE_8G


def stk_init():
    i2c_write_reg(STK_ADDR, STK_REG_SWRST, 0xB6)
    time.sleep_ms(10)
    chip_id = i2c_read_reg(STK_ADDR, STK_REG_CHIP_ID, 1)[0]
    if chip_id != 0x25:
        print("[STK8328] WARNING: chip_id 0x{:02X} (expected 0x25)".format(chip_id))
    else:
        print("[STK8328] chip_id OK: 0x{:02X}".format(chip_id))
    i2c_write_reg(STK_ADDR, STK_REG_POWMODE, 0x80)
    time.sleep_ms(2)
    i2c_write_reg(STK_ADDR, STK_REG_RANGESEL, _stk_range)
    i2c_write_reg(STK_ADDR, STK_REG_BWSEL, STK_BW_125HZ)
    i2c_write_reg(STK_ADDR, STK_REG_POWMODE, 0x00)
    time.sleep_ms(5)


def stk_read_accel():
    raw = i2c_read_reg(STK_ADDR, STK_REG_XOUT1, 6)

    def s16(lo, hi):
        v = (hi << 8) | lo
        return v - 0x10000 if v >= 0x8000 else v

    sens = _STK_SENSITIVITY[_stk_range]
    return (
        s16(raw[0], raw[1]) / sens,
        s16(raw[2], raw[3]) / sens,
        s16(raw[4], raw[5]) / sens,
    )


# WF183DE
WF_ADDR = 0x6D
WF_REG_CMD = 0x0A
WF_REG_PRES = 0x0B
WF_REG_TEMP = 0x0F
WF_REG_STS = 0x13
WF_CMD_TEMP = 0x04
WF_CMD_PRES = 0x06


def _wf_wait(timeout_ms=200):
    t = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(t, time.ticks_ms()) > 0:
        try:
            i2c.writeto(WF_ADDR, bytes([WF_REG_STS]))
            if i2c.readfrom(WF_ADDR, 1)[0] & 0x01:
                return True
        except Exception:
            pass
        time.sleep_ms(5)
    return False


def wf_read_temp():
    i2c.writeto(WF_ADDR, bytes([WF_REG_CMD, WF_CMD_TEMP]))
    _wf_wait()
    i2c.writeto(WF_ADDR, bytes([WF_REG_TEMP]))
    raw = i2c.readfrom(WF_ADDR, 2)
    val = (raw[0] << 8) | raw[1]
    if val >= 0x8000:
        val -= 0x10000
    return val / 10.0


def wf_read_pressure():
    i2c.writeto(WF_ADDR, bytes([WF_REG_CMD, WF_CMD_PRES]))
    _wf_wait()
    i2c.writeto(WF_ADDR, bytes([WF_REG_PRES]))
    raw = i2c.readfrom(WF_ADDR, 4)
    val = (raw[0] << 24) | (raw[1] << 16) | (raw[2] << 8) | raw[3]
    return val / 1000.0


# OLED
OLED_ADDR = 0x3C
OLED_W = 128
OLED_H = 64

_OLED_INIT_CMDS = bytes(
    [
        0xAE,
        0xD5,
        0x80,
        0xA8,
        0x3F,
        0xD3,
        0x00,
        0x40,
        0x8D,
        0x14,
        0x20,
        0x00,
        0xA1,
        0xC8,
        0xDA,
        0x12,
        0x81,
        0xCF,
        0xD9,
        0xF1,
        0xDB,
        0x40,
        0xA4,
        0xA6,
        0xAF,
    ]
)

_oled_buf = bytearray(OLED_W * OLED_H // 8)
_oled_fb = framebuf.FrameBuffer(_oled_buf, OLED_W, OLED_H, framebuf.MONO_VLSB)
_oled_present = False


def _oled_cmds(data):
    for b in data:
        i2c.writeto(OLED_ADDR, bytes([0x00, b]))


def oled_init():
    global _oled_present

    if OLED_ADDR not in i2c.scan():
        print("[OLED]   not found on bus (0x{:02X})".format(OLED_ADDR))
        return False
    try:
        _oled_cmds(_OLED_INIT_CMDS)
        _oled_fb.fill(0)
        oled_show()
        _oled_present = True
        print("[OLED]   initialised (128x64, 4-pin no reset)")
        return True
    except Exception as e:
        print("[OLED]   init error:", e)
        return False


def oled_show():
    if not _oled_present:
        return
    _oled_cmds(bytes([0x21, 0, 127, 0x22, 0, 7]))
    chunk = 16
    for offset in range(0, len(_oled_buf), chunk):
        i2c.writeto(OLED_ADDR, b"\x40" + _oled_buf[offset : offset + chunk])


def oled_update(ax, ay, az, t_wf, pres):
    fb = _oled_fb
    fb.fill(0)

    fb.fill_rect(0, 0, 128, 12, 1)
    fb.text("HERMES SENSORS", 8, 2, 0)

    fb.text("STK8328", 4, 16, 1)
    fb.text("X: {:.2f} g".format(ax if ax is not None else 0), 4, 28, 1)
    fb.text("Y: {:.2f} g".format(ay if ay is not None else 0), 4, 40, 1)
    fb.text("Z: {:.2f} g".format(az if az is not None else 0), 4, 52, 1)
    fb.vline(82, 16, 48, 1)
    fb.text("WF183", 88, 16, 1)

    if t_wf is not None:
        fb.text("{:.1f}C".format(t_wf), 88, 32, 1)
    else:
        fb.text("T:N/A", 88, 32, 1)

    if pres is not None:
        fb.text("{:.1f}".format(pres), 88, 44, 1)
        fb.text("kPa", 88, 54, 1)
    else:
        fb.text("P:N/A", 88, 44, 1)

    oled_show()


# Main


def scan_bus():
    devices = i2c.scan()
    print("I2C scan:", [hex(d) for d in devices])


def main():
    print("=" * 50)
    print("  Hermes Sensor Board - MicroPython")
    print("=" * 50)

    time.sleep_ms(200)
    scan_bus()

    print("\nInitialising sensors...")
    stk_init()
    print("[WF183DE] ready")
    oled_init()

    print("\nStarting read loop. Press Ctrl-C to stop.\n")
    print(
        "{:>8} | {:>7} {:>7} {:>7} | {:>11} {:>9} | {:>10} {:>10}".format(
            "Time(s)", "Ax(g)", "Ay(g)", "Az(g)", "Temp_WF", "Pres(kPa)"
        )
    )
    print("-" * 85)

    t0 = time.ticks_ms()

    def fmt(v, w, d):
        return (
            "{:>{}.{}f}".format(v, w, d)
            if v is not None
            else "{:>{}s}".format("N/A", w)
        )

    while True:
        elapsed = time.ticks_diff(time.ticks_ms(), t0) / 1000.0

        try:
            ax, ay, az = stk_read_accel()
        except Exception as e:
            ax = ay = az = None
            print("[STK8328] read error:", e)

        try:
            t_wf = wf_read_temp()
            pres = wf_read_pressure()
        except Exception as e:
            t_wf = pres = None
            print("[WF183DE] read error:", e)

        print(
            "{:>8.1f} | {} {} {} | {} {} | {} {}".format(
                elapsed,
                fmt(ax, 7, 3),
                fmt(ay, 7, 3),
                fmt(az, 7, 3),
                fmt(t_wf, 10, 1),
                fmt(pres, 10, 3),
            )
        )

        # OLED update (Passing STK and WF stats)
        if _oled_present:
            try:
                oled_update(ax, ay, az, t_wf, pres)
            except Exception as e:
                print("[OLED]   display error:", e)

        time.sleep_ms(1000)


if __name__ == "__main__":
    main()
