"""Capture the FIR test dump from the board and plot it like lecture slide 17.

The board prints one block over UART1 after the FIR test:

    BEGIN FIR
    0,<input>,<output>
    1,<input>,<output>
    ...
    END FIR

Usage:
    uv run plot_fir.py --port COM5            # capture, save CSV, plot
    uv run plot_fir.py --csv fir_dump.csv     # plot a saved CSV again
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

FS_HZ = 48_000      # sample rate of the arm_fir_example test signal
CUTOFF_HZ = 6_000   # cutoff of the fir1(28, 6/24) low-pass filter
NFFT = 2048         # zero-padded FFT length, for a smooth spectrum curve

# Colors: categorical slots 1 and 2 of the reference palette, light mode.
INPUT_COLOR = "#2a78d6"
OUTPUT_COLOR = "#eb6834"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e4e3df"


def parse_dump(lines):
    """Return (n, x, y) arrays from the lines between BEGIN FIR and END FIR."""
    rows = []
    inside = False
    for line in lines:
        line = line.strip()
        if line == "BEGIN FIR":
            inside, rows = True, []
        elif line == "END FIR":
            if inside:
                break
        elif inside and line:
            n, x, y = line.split(",")
            rows.append((int(n), float(x), float(y)))
    else:
        raise ValueError("no complete 'BEGIN FIR' ... 'END FIR' block found")
    data = np.array(rows)
    return data[:, 0].astype(int), data[:, 1], data[:, 2]


def capture(port, baud):
    """Read lines from the serial port until one full dump block arrives."""
    import serial

    def lines():
        with serial.Serial(port, baud, timeout=None) as ser:
            print(f"Listening on {port}. Press the black RESET button on the board.")
            while True:
                yield ser.readline().decode("ascii", errors="replace")

    return parse_dump(lines())


def save_csv(path, n, x, y):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "input", "output"])
        w.writerows(zip(n, x, y))


def load_csv(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0].astype(int), data[:, 1], data[:, 2]


def spectrum(signal):
    """One-sided amplitude spectrum, scaled so a sine of amplitude A peaks near A."""
    mag = np.abs(np.fft.rfft(signal, NFFT)) * 2 / len(signal)
    freq = np.fft.rfftfreq(NFFT, d=1 / FS_HZ)
    return freq, mag


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelcolor=INK_MUTED)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)


def plot(n, x, y, out_stem):
    fig, axes = plt.subplots(2, 2, figsize=(10, 5.6), layout="constrained")
    rows = [
        (x, "Input x[n]: 1 kHz + 15 kHz", "|X(f)|", INPUT_COLOR),
        (y, "Output y[n]: after the FIR low-pass filter", "|Y(f)|", OUTPUT_COLOR),
    ]
    mag_max = max(spectrum(x)[1].max(), spectrum(y)[1].max())

    for (sig, title, mag_label, color), (ax_t, ax_f) in zip(rows, axes):
        ax_t.plot(n, sig, color=color, linewidth=1.5)
        ax_t.set_title(title, loc="left", fontsize=11)
        ax_t.set_xlabel("Sample n")
        ax_t.set_ylabel("Amplitude")
        ax_t.set_xlim(n[0], n[-1])
        ax_t.set_ylim(-1.5, 1.5)
        style(ax_t)

        freq, mag = spectrum(sig)
        ax_f.plot(freq / 1000, mag, color=color, linewidth=1.5)
        ax_f.axvline(CUTOFF_HZ / 1000, color=INK_MUTED, linewidth=1, linestyle="--")
        ax_f.text(CUTOFF_HZ / 1000 + 0.3, mag_max * 1.02, "6 kHz cutoff",
                  color=INK_MUTED, fontsize=9, va="top")
        ax_f.set_title(f"Spectrum {mag_label}", loc="left", fontsize=11)
        ax_f.set_xlabel("Frequency (kHz)")
        ax_f.set_ylabel("Magnitude")
        ax_f.set_xlim(0, FS_HZ / 2000)
        ax_f.set_ylim(0, mag_max * 1.08)
        style(ax_f)

    for ext in ("png", "pdf"):
        path = out_stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=200)
        print(f"Saved {path}")
    plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="serial port of the ST-Link, for example COM5")
    src.add_argument("--csv", type=Path, help="plot a CSV from an earlier capture")
    ap.add_argument("--baud", type=int, default=1_000_000,
                    help="must match USART1 in lab7.ioc (default 1000000)")
    ap.add_argument("--out", type=Path, default=Path("fir_known_signal"),
                    help="output file stem; the script writes .csv, .png and .pdf")
    args = ap.parse_args()

    if args.port:
        n, x, y = capture(args.port, args.baud)
        csv_path = args.out.with_suffix(".csv")
        save_csv(csv_path, n, x, y)
        print(f"Captured {len(n)} samples, saved {csv_path}")
    else:
        n, x, y = load_csv(args.csv)

    plot(n, x, y, args.out)


if __name__ == "__main__":
    main()
