# Scan, then choose the entry where getValueText(3) contains fff0. A name match on OLDPIG123_HOST also works.
# Peripheral(addr, 'random').
# Get the characteristic with getCharacteristics(uuid=UUID(0xfff1))[0].
# Get its CCCD with getDescriptors(forUUID=0x2902)[0].
# Write b"\x02\x00" with withResponse=True.
# Read it back and print it.
# Disconnect in a finally.

from bluepy.btle import Scanner, Peripheral, UUID, BTLEException

scanner = Scanner()
print("Scanning for 8 seconds...")
scan_entries = scanner.scan(8.0)

for entry in scan_entries:
    text = entry.getValueText(3)
    # check text is not None before checking for substring 
    if text is None:
        continue
    if "fff0" in text:
        print(f"Found device: {entry.addr}")
        break
else:
    print("No device found with UUID fff0.")
    exit(1)

peripheral = Peripheral(entry.addr, 'random')
try:
    # Get the characteristic with getCharacteristics(uuid=UUID(0xfff1))[0].
    char = peripheral.getCharacteristics(uuid=UUID(0xfff1))[0]

    print(char.propertiesToString())  # prints "INDICATE"
    # Get its CCCD with getDescriptors(forUUID=0x2902)[0].
    cccd = char.getDescriptors(forUUID=0x2902)[0]

    print(f"CCCD handle: 0x{cccd.handle:04x}")  # prints 0x000e
    print("1 for notification, 2 for indication.")
    # Write b"\x02\x00" with withResponse=True.
    cccd.write(b"\x02\x00", withResponse=True)
    # Read it back and print it.
    value = cccd.read()
    n = int.from_bytes(value, "little")
    print(f"CCCD value: 0x{n:04x}")      # prints 0x0002

finally:
    # Disconnect in a finally.
    peripheral.disconnect()

    