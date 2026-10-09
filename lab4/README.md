# Lab4: BLE GATT Accelerometer Service with FreeRTOS

## Overview
The STM32 B-L475E-IOT01A board acts as a **BLE GATT server** (peripheral) and a Raspberry Pi acts as a **GATT client** (central).
The board exposes a custom accelerometer service with three characteristics:
- **(a) 3-axis acceleration**: real LSM6DSL data, pushed to the Pi with notifications
- **(b) sampling frequency**: the Pi writes it to set how often the board samples and notifies
- **(c) significant motion event** (Option 1(b)): notified when the LSM6DSL detects significant motion

The firmware runs on FreeRTOS (CMSIS-RTOS v2) with two tasks, `TASK_BLE` and `TASK_ACC`.

## Lab requirements

### Basic: GATT accelerometer service + RTOS tasks

#### GATT service
The board advertises with the complete local name **`ES_HENG`**.

| Item | UUID | Properties | Value format |
|------|------|------------|--------------|
| Accelerometer service | `0a38e701-0511-49c1-ba27-5ffb911242a4` | Primary | — |
| (a) Acceleration XYZ | `0a38e702-0511-49c1-ba27-5ffb911242a4` | Notify | 6 bytes: `int16` X, Y, Z in **mg**, little-endian |
| (b) Sampling frequency | `0a38e703-0511-49c1-ba27-5ffb911242a4` | Write, Write Without Response | 1 byte: `uint8` frequency in **Hz** (default 2 Hz) |
| (c) Significant motion | `0a38e704-0511-49c1-ba27-5ffb911242a4` | Notify | 1 byte: `0x01` when an event occurs |

Example notification payload with the board lying flat: `03 00 FE FF E8 03` → X = 3, Y = -2, Z = 1000 mg.

The service reserves 9 attribute records: the service declaration, 3 for characteristic (a) (declaration, value, CCCD), 2 for characteristic (b) (declaration, value), and 3 for characteristic (c) (declaration, value, CCCD).

#### RTOS tasks

| Task | Priority | Stack | Responsibility |
|------|----------|-------|----------------|
| `TASK_BLE` | Normal | 1024 words | Restarts advertising when `set_connectable` is set (at boot and after each disconnection). Calls `hci_user_evt_proc()` every 5 ms to dispatch BlueNRG events: GAP connection complete, GAP disconnection complete, and GATT attribute modified (the write to characteristic (b)). |
| `TASK_ACC` | AboveNormal | 512 words | Reads the LSM6DSL over I2C2, converts the raw values to mg, and calls `aci_gatt_update_char_value()` on characteristic (a) while a client is connected. Waits up to `1000 / acc_freq_hz` ms between samples with `osThreadFlagsWait`; wakes early when the significant motion EXTI sets thread flag `0x01`, then reads `FUNC_SRC1` and notifies characteristic (c). |

- **`bleMutex`**: both tasks send HCI commands to the BlueNRG-MS over SPI3. The HCI layer (`hci_send_req`) waits for the command-complete event on a single global event queue. If one task preempted the other, it could consume the reply meant for the other task's command, so every BlueNRG call is wrapped in `osMutexAcquire` / `osMutexRelease`.
- **`acc_freq_hz`**: written in `TASK_BLE` (from the attribute-modified event) and read in `TASK_ACC`. It is a `volatile uint8_t`. A single-byte load/store is atomic on the Cortex-M4, so no lock is needed.

#### Accelerometer access
The LSM6DSL is accessed by reading and writing registers directly through `HAL_I2C_Mem_Read/Write` on `hi2c2` (I2C address `0xD4`):
- `CTRL3_C = 0x44`: block data update + register address auto-increment
- `CTRL1_XL = 0x40`: ODR 104 Hz, ±2 g full scale (0.061 mg/LSB)
- Each sample reads 6 bytes starting at `OUTX_L_XL` (`0x28`)

### Option 1(b): Significant motion detection
The LSM6DSL's embedded significant motion function (pedometer based; fires after `SM_THS` = 6 steps by default, needs ODR ≥ 26 Hz) is routed to its INT1 pin, which is wired to **PD11 (EXTI11)** on the board.
- `CTRL10_C (0x19) = 0x05`: `FUNC_EN` + `SIGN_MOTION_EN`
- `INT1_CTRL (0x0D) = 0x40`: `INT1_SIGN_MOT`, route the event to INT1
- `FUNC_SRC1 (0x53)` bit 6 `SIGN_MOTION_IA`: confirms the event; read once at init and after each interrupt to clear it

Flow: INT1 rising edge → `EXTI15_10_IRQHandler` → `HAL_GPIO_EXTI_Callback` calls `osThreadFlagsSet(TASK_ACCHandle, 0x01)` → `TASK_ACC` wakes from `osThreadFlagsWait`, reads `FUNC_SRC1` over I2C2, and if bit 6 is set and a client is connected, notifies characteristic (c) under `bleMutex`.
The ISR only sets a flag because I2C reads and BlueNRG HCI commands block and use the mutex, which is not allowed in interrupt context. The event is handled in `TASK_ACC` because it is the only task that uses I2C2.
`osThreadFlagsWait` returns `osFlagsErrorTimeout` (`0xFFFFFFFE`) on timeout, whose bit 0 is also 1, so the code checks that bit 31 is 0 before testing bit 0.


## Build Instructions

### STM32 Firmware

**Prerequisites**
- STM32CubeIDE (the project was generated with STM32CubeMX 6.18.1)
- STM32Cube FW_L4 V1.18.2
- X-CUBE-BLE1 7.0.0

All required driver and middleware sources are already included in `STM32/Lab4`, so no code generation is needed.

1. In STM32CubeIDE, choose **File → Import → General → Existing Projects into Workspace**, and select the `lab4/STM32/Lab4` folder.
2. **Project → Build Project** (Debug configuration).
3. Connect the board through the ST-LINK USB port and choose **Run → Run** (or use `Lab4.launch`).
4. After reset, the board starts advertising as `ES_HENG`.

> **Do not click "Generate Code" in CubeMX without checking the diff afterwards.**
> `BlueNRG_MS/App/sensor.c` and `sensor.h` have no `USER CODE` sections, so CubeMX overwrites them.
> If you regenerate, re-apply these changes: the device name in `sensor.h` and the `EVT_BLUE_GATT_ATTRIBUTE_MODIFIED` case plus the `#include "acc_service.h"` line in `sensor.c`.

### Raspberry Pi Client

**Prerequisites**: Python 3, BlueZ, and `bluepy`. Building `bluepy-helper` requires the glib headers.

```bash
sudo apt install libglib2.0-dev
python3 -m venv .venv
source .venv/bin/activate
pip install bluepy
```

Run the client. Root privileges are needed for scanning. Call the venv interpreter explicitly, because `sudo` resets `PATH` and `sudo python` would use the system Python, which does not have bluepy:

```bash
sudo .venv/bin/python rpi/central.py 10    # set the sampling frequency to 10 Hz
sudo .venv/bin/python rpi/central.py       # keep the current frequency (2 Hz after reset)
```

The script:
1. scans for 5 s and selects the device named `ES_HENG`
2. connects and looks up the service and both characteristics by UUID
3. enables notifications by writing `01 00` to the CCCDs of characteristics (a) and (c)
4. if a frequency argument is given, writes it as 1 byte to characteristic (b)
5. for 60 seconds, prints the decoded X / Y / Z values (mg) for 6-byte notifications and `Significant motion detected` for 1-byte notifications, then disconnects

Expected output with the board lying flat, at 10 Hz (about 10 lines per second):
```
Notification from handle 0x00xx: X=3, Y=-2, Z=1000
```
To trigger significant motion, hold the board and move it up and down like walking (about one step per second, 6+ steps):
```
Notification from handle 0x00xx: Significant motion detected
```

If the board is not found, check that it is advertising with `bluetoothctl --timeout 15 scan le`.

## Project Structure
```
lab4/
  STM32/Lab4/                     # Complete STM32CubeIDE project (CubeMX: Lab4.ioc)
    Core/Src/main.c               # FreeRTOS tasks TASK_BLE / TASK_ACC, LSM6DSL register access, EXTI callback
    Core/Src/acc_service.c        # Custom GATT service: creation, notify, write handler
    Core/Inc/acc_service.h
    BlueNRG_MS/App/app_bluenrg_ms.c  # BLE init: GAP device name, calls Add_Acc_Service()
    BlueNRG_MS/App/sensor.c       # HCI event dispatch (adds the attribute-modified case)
    BlueNRG_MS/App/sensor.h       # Advertised name ES_HENG
  rpi/
    central.py                    # bluepy GATT client: subscribe to XYZ and motion, write frequency
```

### Changes relative to the CubeMX SensorDemo template

| File | Change |
|------|--------|
| `Lab4.ioc` | FreeRTOS (CMSIS_V2) enabled; tasks `TASK_BLE` and `TASK_ACC`; mutex `bleMutex`; TIM6 as the HAL timebase |
| `Core/Src/acc_service.c/.h` | New files. `Add_Acc_Service()`, `Acc_Service_Notify()`, `Acc_Service_Motion_Notify()`, `Acc_Service_Attr_Modified()`, `acc_freq_hz` |
| `Core/Src/main.c` | Task bodies and `HAL_GPIO_EXTI_Callback` (PD11 → thread flag). `TASK_BLE` replaces `MX_BlueNRG_MS_Process()` to drop SensorDemo's simulated data and its blocking `HAL_Delay(1000)` |
| `BlueNRG_MS/App/app_bluenrg_ms.c` | Inside `USER CODE` sections: set GAP device name, call `Add_Acc_Service()` |
| `BlueNRG_MS/App/sensor.c` | Dispatch `EVT_BLUE_GATT_ATTRIBUTE_MODIFIED` to `Acc_Service_Attr_Modified()` |
| `BlueNRG_MS/App/sensor.h` | `SENSOR_DEMO_NAME` changed to `ES_HENG` |
