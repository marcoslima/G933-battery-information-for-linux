"""
A3tra3rpi 2019
Absolutely no warranty
Work in progress. Battery levels are not 100% accurate > mostly guesses based
on logged values. Also currently disconnects audio temporarily for the
communication
Requires pyusb and needs to be ran as su
Usage: sudo python3 g933battery.py
"""

import sys

# noinspection PyPackageRequirements
import usb


class BatteryStatus:
    def __init__(self, data):
        self.data = data
        self.size = len(data)

    def _get_data(self, index):
        return self.data[index] if self.size > index else 0

    @property
    def b1(self):
        return self._get_data(4) - 13  # 13-15 > 0-2

    @property
    def b2(self):
        return self._get_data(5)

    @property
    def state(self):
        return self._get_data(6)

    @property
    def status(self):
        # Current best effort trying to extract battery status
        return self._level if self.state != 0 else 0

    @property
    def status_text(self):
        statuses = {
            0: "Disconnected",
            1: "Idle",
            3: "Charging",
        }

        return statuses.get(self.state,
                            f'Not implemented({hex(self.state)})')

    @property
    def is_valid(self):
        return self.size > 6 and self.state not in [135, 145]

    def __repr__(self):
        return f'Battery:~{self.status}% (estimated from: ' \
               f'{self.b1}/2, {self.b2}/255)'

    @property
    def _level(self) -> int:
        """
        CHARGING AND DISCHARGING LEVELS ARE DIFFERENT.
        This is based on the levels seen when discharging
        b1 from d to f (might temporarily go c and 10)
        b2 from 0 to 255 for every b1 value
        Shutdown at about b1:0xd, b2:0x0 and full capacity
        about b1:0xf, b2:0xff
        """
        lvl = self.b1
        mx = 0xff
        return int(((self.b2 + lvl * mx) * 100) / (3 * mx))


class G933BatteryStatus:
    VID = 0x046d  # Logitech
    PID = 0x0a5b  # G933 (G930 might work? Not tested)

    def __init__(self):
        pass

    def get_battery_state(self):
        dev = self._open_device()
        endpoint_in = self._get_endpoint_in(dev)
        try:
            while self._read_device(dev, endpoint_in):
                pass

        except Exception as e:
            msg = f'Exception: {e.__class__.__name__}({e})'
            print(msg)

        self._close_device(dev)

    @staticmethod
    def _get_endpoint_in(dev):
        for cfg in dev:
            for intf in cfg:
                if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        dev.detach_kernel_driver(intf.bInterfaceNumber)
                    except usb.core.USBError as e:
                        msg = f'Could not detach kernel driver from ' \
                              f'interface({intf.bInterfaceNumber}):{str(e)}'
                        sys.exit(msg)

        return dev[0][(3, 0)][0]

    @staticmethod
    def _read_device(dev, endpoint_in) -> bool:
        # 21 09 11 02 03 00 00 00
        # |  |  |     |     |
        # |  |  Value Index Length
        # |  Request
        # Request type
        # 0x21, 0x09, 0x0211, 0x0003
        # and data:
        # 11ff080a00000000000000000000000000000000
        # or     |
        # 11ff080b00000000000000000000000000000000
        # or     |
        # 11ff080c00000000000000000000000000000000
        dev.ctrl_transfer(0x21, 0x09, 0x0211, 0x0003,
                          [0x11, 0xFF, 0x08, 0x0a, 0x00, 0x00, 0x00, 0x00,
                           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                           0x00, 0x00, 0x00, 0x00])
        data = dev.read(endpoint_in.bEndpointAddress,
                        endpoint_in.wMaxPacketSize,
                        0)  # Receive data from usb
        # print_hex(data) #Print received data
        # Received packet contains supposed battery data
        # from byte[3] to byte[6]:
        # 0xa 0xf 0xe9 0x1
        # |   |   |    |
        # |   |   |    Headset status
        # |   |   Battery level pt2
        # |   Battery level pt1
        # Unknown level. Often 0xa or 0xc

        # Packet with byte 6 of 135 or 145 is some other packet and
        # might not contain any data about the battery
        bstatus = BatteryStatus(data)
        if bstatus.is_valid:
            print(bstatus)
            print("Status:", bstatus.status_text)
            return False
        return True

    @staticmethod
    def _close_device(dev):
        dev.attach_kernel_driver(0)
        usb.util.dispose_resources(dev)

    def _open_device(self):
        dev = usb.core.find(idVendor=self.VID, idProduct=self.PID)
        if not dev:
            print("Could not find device")
            sys.exit(1)
        return dev


def main():
    gbs = G933BatteryStatus()

    try:
        gbs.get_battery_state()
    except Exception as e:
        msg = f'{e.__class__.__name__}({e})'
        print(msg)
        exit(1)


if __name__ == '__main__':
    main()
