# server.py: stand-in for the Android "BLE Tool" GATT server, run on the Windows laptop.
# Advertises service 0xFFF0 with one indicate-only characteristic 0xFFF1 and logs
# every time a central changes its subscription (i.e. writes the CCCD).
import asyncio
import time
import uuid

from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattCharacteristicProperties,
    GattLocalCharacteristicParameters,
    GattServiceProvider,
    GattServiceProviderAdvertisingParameters,
)

SERVICE_UUID = uuid.UUID("0000fff0-0000-1000-8000-00805f9b34fb")
CHAR_UUID = uuid.UUID("0000fff1-0000-1000-8000-00805f9b34fb")


def on_subscribed_clients_changed(sender, args):
    # Windows owns the CCCD, so the raw 0x0001/0x0002 value is not visible here;
    # we can only see who is subscribed. The characteristic is indicate-only, so a
    # subscription can only come from a CCCD write of 0x0002.
    n = len(sender.subscribed_clients)
    print(f"[{time.strftime('%H:%M:%S')}] CCCD changed on {CHAR_UUID}: {n} subscribed client(s)", flush=True)


async def main():
    result = await GattServiceProvider.create_async(SERVICE_UUID)
    provider = result.service_provider

    params = GattLocalCharacteristicParameters()
    params.characteristic_properties = GattCharacteristicProperties.INDICATE
    char_result = await provider.service.create_characteristic_async(CHAR_UUID, params)
    char_result.characteristic.add_subscribed_clients_changed(on_subscribed_clients_changed)

    adv = GattServiceProviderAdvertisingParameters()
    adv.is_discoverable = True
    adv.is_connectable = True
    provider.start_advertising_with_parameters(adv)
    print(f"Advertising service {SERVICE_UUID}. Ctrl+C to stop.", flush=True)
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        provider.stop_advertising()


asyncio.run(main())
