# Lab6: Data Acquisition with ADC, Timer, DMA and FreeRTOS

| Project | Description |
|---|---|
| `STM32/lab6` | Problem 1: TIM1 (1 Hz) triggers ADC1 to sample the internal temperature sensor. The ADC interrupt sends each value to a FreeRTOS task, which prints it over UART. |
| `STM32/lab6_2` | Problem 2: TIM1 (20 Hz) triggers ADC1, and DMA fills a 256-sample circular buffer. The task prints each half of the buffer when it is full. |
| `STM32/lab6_op1` | Option 1: DFSDM1 + DMA read the on-board MP34DT01 microphone into `RecBuf` continuously, following ST's [STM32L4 training: Hands-on DFSDM](https://www.youtube.com/watch?v=MdDqVeIGhec). |

## Build and Run

Requirements: STM32CubeIDE and the B-L475E-IOT01A board. All driver sources are included, so no code generation is needed.

1. In STM32CubeIDE, choose **File → Import → General → Existing Projects into Workspace** and select one of the folders above.
2. **Project → Build Project**.
3. Connect the board through the ST-LINK USB port.
4. Run the project:
   - Problem 1 and Problem 2: **Run → Run**. Open the **STLink Virtual COM Port** (find the COM number in Device Manager) at **115200** baud in PuTTY or Tera Term.
   - Option 1: **Run → Debug**. There is no UART output.

## Expected Output

**Problem 1**: one line per second.
```
Tick 36714: raw=946, temperature=30
Tick 37714: raw=947, temperature=30
```
Press a finger on the STM32 chip, and the value rises within a few seconds.

**Problem 2**: one block every 6.4 s. `half` alternates between 0 and 1.
```
Tick 6168: half=0, index=[0...127]
  949  950  948  949  950  951  951  949  948  950  949  949  950  951  950  949
  ... (8 lines in total)
Avg: raw=949, temp=30
```

**Option 1**: in Debug mode, add `RecBuf` and `PlayBuf` to the **Expressions** view. Set a breakpoint inside `if (DmaRecHalfBuffCplt == 1)` or `if (DmaRecBuffCplt == 1)` in `main.c`, then resume several times. The values in both buffers change every time the program stops, which shows that microphone data is being received. `PlayBuf[i]` is `RecBuf[i] >> 8`.
