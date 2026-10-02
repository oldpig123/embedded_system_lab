# Lab2: Sensor Reading and WiFi Communication

## Overview
Read onboard sensor data from the STM32 B-L475E-IOT01A board, transmit via WiFi TCP to a host PC, and visualize in real-time using Python matplotlib.

## Features

### Basic: Accelerometer WiFi Streaming (85 pts)
- Read LSM6DSL 3-axis accelerometer data using BSP API (`BSP_ACCELERO_AccGetXYZ`)
- Board acts as TCP Client, connects to a Python TCP Server on the host PC (port 8002)
- Python server plots X/Y/Z acceleration in real-time

### Option A: Significant Motion Detection (+5 pts)
- Enable LSM6DSL hardware significant motion detection by writing registers directly via `SENSOR_IO_Write`
- Configuration procedure follows AN5040 Application Note:
  1. Switch to embedded function register bank (FUNC_CFG_ACCESS = 0x80)
  2. Set significant motion threshold (SM_THS = 0x08, triggers after 8 step-like motions)
  3. Switch back to main bank (FUNC_CFG_ACCESS = 0x00)
  4. Set accelerometer ODR to 26Hz (CTRL1_XL = 0x20)
  5. Enable embedded functions + significant motion (CTRL10_C = 0x05)
  6. Route significant motion interrupt to INT1 pin (INT1_CTRL bit 6 = 1)
- Configure STM32 GPIO PD11 (LSM6DSL INT1 pin) as EXTI rising edge interrupt
- Register `EXTI15_10_IRQHandler` → `HAL_GPIO_EXTI_Callback` to handle the interrupt
- On trigger, send `MOTION\n` to the PC; Python displays red dashed lines on the accelerometer chart
- SM_THS threshold is adjustable: lower value = more sensitive, higher value = requires more shaking

### Option B: Multi-Sensor Dashboard (+5 pts)
- Read all onboard I2C sensors:

  | Sensor | IC | BSP API | Unit |
  |--------|----|---------|------|
  | Accelerometer | LSM6DSL | `BSP_ACCELERO_AccGetXYZ` | mg |
  | Gyroscope | LSM6DSL | `BSP_GYRO_GetXYZ` | mdps |
  | Magnetometer | LIS3MDL | `BSP_MAGNETO_GetXYZ` | mGauss |
  | Temperature | HTS221 | `BSP_TSENSOR_ReadTemp` | °C |
  | Humidity | HTS221 | `BSP_HSENSOR_ReadHumidity` | % |
  | Pressure | LPS22HB | `BSP_PSENSOR_ReadPressure` | hPa |

- Python displays a 2×2 real-time dashboard:
  - Top-left: Accelerometer XYZ (with motion event markers)
  - Top-right: Gyroscope XYZ
  - Bottom-left: Magnetometer XYZ
  - Bottom-right: Environment (temperature + humidity curves, title shows current values including pressure)
- Sliding window keeps the latest 100 data points

## Build Instructions

### STM32 Firmware

**Prerequisites**: STM32CubeIDE + STM32CubeL4 SDK

1. Open STM32CubeIDE and import the WiFi_Client_Server example project from the SDK:
   ```
   STM32CubeL4/Projects/B-L475E-IOT01A/Applications/WiFi/WiFi_Client_Server/
   ```

2. Replace the following files in the project with the ones from this repo:
   - `STM32/Src/main.c` → project's `Src/main.c`
   - `STM32/Src/stm32l4xx_it.c` → project's `Src/stm32l4xx_it.c`
   - `STM32/Inc/main.h` → project's `Inc/main.h`

3. Add BSP driver source files to the project (right-click → Add existing files):
   - From `Drivers/BSP/B-L475E-IOT01/`:
     - `stm32l475e_iot01_gyro.c`
     - `stm32l475e_iot01_tsensor.c`
     - `stm32l475e_iot01_hsensor.c`
     - `stm32l475e_iot01_psensor.c`
     - `stm32l475e_iot01_magneto.c`
   - From `Drivers/BSP/Components/`:
     - `lsm6dsl/lsm6dsl.c` (if not already in the project)
     - `lis3mdl/lis3mdl.c`
     - `hts221/hts221.c`
     - `lps22hb/lps22hb.c`

4. Update network settings in `main.c`:
   ```c
   #define SSID     "your_wifi_ssid"
   #define PASSWORD "your_wifi_password"
   uint8_t RemoteIP[] = {192, 168, 1, 100};  // your PC's IP address
   ```

5. Build and flash to the board via ST-LINK

### Python TCP Server

**Prerequisites**: Python 3.x

```bash
pip install matplotlib PyQt5
python tcp_server.py
```

The server listens on port 8002 and waits for the board to connect. **Start the Python server first, then reset the board.**

If Windows Firewall blocks the connection, run in an admin PowerShell:
```powershell
netsh advfirewall firewall add rule name="Python TCP Server" dir=in action=allow program="C:\path\to\python.exe" protocol=tcp localport=8002
```

## Project Structure
```
lab2/
  STM32/
    Src/main.c            # Main program (WiFi + all sensors + significant motion)
    Src/stm32l4xx_it.c    # Interrupt handlers (EXTI1: WiFi SPI, EXTI15_10: LSM6DSL INT1)
    Inc/main.h            # Header with BSP includes for all sensors
  python/
    tcp_server.py         # TCP server + 2×2 real-time matplotlib dashboard
```