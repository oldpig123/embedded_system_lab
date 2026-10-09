import sys
import time
import struct
from bluepy.btle import Peripheral, UUID
from bluepy.btle import Scanner, DefaultDelegate

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print ("Discovered device", dev.addr)
        elif isNewData:
            print ("Received new data from", dev.addr)

class NotificationDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
    def handleNotification(self, cHandle, data):
        if len(data) == 6:
            x, y, z = struct.unpack('<hhh', data)
            print(f"Notification from handle 0x{cHandle:04X}: X={x}, Y={y}, Z={z}")
        elif len(data) == 1:
            print(f"Notification from handle 0x{cHandle:04X}: Significant motion detected")

# 1. Scan for BLE devices and pick the one advertising the name ES_HENG
scanner = Scanner().withDelegate(ScanDelegate())
devices = scanner.scan(5.0)
target_device, rssi = None, -1e10

for dev in devices:
    if dev.getValue(0x09) == "ES_HENG":
        print("Found device named ES_HENG")
        print("Device %s (%s), RSSI=%d dB, complete local name: %s" % (dev.addr, dev.addrType, dev.rssi, dev.getValue(0x09)))
        if dev.rssi > rssi:
            rssi = dev.rssi
            target_device = dev

if target_device is None:
    print("No device named ES_HENG found.")
    sys.exit(1)

# 2. Connect
print("Connecting to device %s (%s)" % (target_device.addr, target_device.addrType))
peripheral_device = Peripheral(target_device)

try:
    # 3. Find the accelerometer service and its XYZ / frequency characteristics
    target_service = peripheral_device.getServiceByUUID(UUID("0a38e701-0511-49c1-ba27-5ffb911242a4"))
    acc_char = target_service.getCharacteristics(UUID("0a38e702-0511-49c1-ba27-5ffb911242a4"))
    freq_char = target_service.getCharacteristics(UUID("0a38e703-0511-49c1-ba27-5ffb911242a4"))
    motion_char = target_service.getCharacteristics(UUID("0a38e704-0511-49c1-ba27-5ffb911242a4"))
    if len(acc_char) == 0:
        print("Characteristic with UUID 0a38e702-0511-49c1-ba27-5ffb911242a4 not found.")
        sys.exit(1)
    if len(freq_char) == 0:
        print("Characteristic with UUID 0a38e703-0511-49c1-ba27-5ffb911242a4 not found.")
        sys.exit(1)
    if len(motion_char) == 0:
        print("Characteristic with UUID 0a38e704-0511-49c1-ba27-5ffb911242a4 not found.")
        sys.exit(1)

    acc_char = acc_char[0]
    freq_char = freq_char[0]
    motion_char = motion_char[0]

    acc_cccd = acc_char.getDescriptors(forUUID=0x2902)
    if len(acc_cccd) == 0:
        print("CCCD descriptor not found for the XYZ characteristic.")
        sys.exit(1)
    acc_cccd = acc_cccd[0]
    print("Found XYZ characteristic and its CCCD descriptor: handle 0x%04X, uuid %s" % (acc_cccd.handle, acc_cccd.uuid))

    motion_cccd = motion_char.getDescriptors(forUUID=0x2902)
    if len(motion_cccd) == 0:
        print("CCCD descriptor not found for the motion characteristic.")
        sys.exit(1)
    motion_cccd = motion_cccd[0]
    print("Found motion characteristic and its CCCD descriptor: handle 0x%04X, uuid %s" % (motion_cccd.handle, motion_cccd.uuid))

    # 4. Enable notifications (CCCD = 0x0001)
    print("CCCD value before writing: 0x%04X" % int.from_bytes(acc_cccd.read(), 'little'))
    acc_cccd.write(b'\x01\x00', withResponse=True)
    print("CCCD value after writing: 0x%04X" % int.from_bytes(acc_cccd.read(), 'little'))
    motion_cccd.write(b'\x01\x00', withResponse=True)

    # 5. Optionally set the sampling frequency in Hz (python central.py <freq>)
    if len(sys.argv) > 1:
        freq = int(sys.argv[1])
        freq_char.write(bytes([freq]), withResponse=True)

    # 6. Print notifications for 60 seconds
    print("Waiting for notifications for 60 seconds...")
    remain_sec = 60.0
    peripheral_device.withDelegate(NotificationDelegate())
    while remain_sec > 0:
        start_time = time.time()
        peripheral_device.waitForNotifications(remain_sec)
        elapsed_time = time.time() - start_time
        remain_sec -= elapsed_time
finally:
    peripheral_device.disconnect() 