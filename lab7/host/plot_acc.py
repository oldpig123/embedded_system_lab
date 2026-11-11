"""Capture raw and FIR-filtered accelerometer data from the board and plot it.

The board prints one start line, then one line per sample (in blocks):

    BEGIN ACC
    0,<raw_z>,<filtered_z>
    1,<raw_z>,<filtered_z>
    ...

Usage:
    uv run plot_acc.py --port COM3 --seconds 10   # capture, save CSV, plot
    uv run plot_acc.py --csv acc_z.csv            # plot a saved CSV again
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

FS_HZ = 50          # sample rate of the 50 Hz schedule in main.c
CUTOFF_HZ = 5       # cutoff of the design_fir.py default filter

# Colors: categorical slots 1 and 2 of the reference palette, light mode.
RAW_COLOR = "#2a78d6"
FILT_COLOR = "#eb6834"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e4e3df"


def parse_stream(lines, max_samples):
    """Return (n, raw, filt) arrays from the lines after BEGIN ACC.

    Stops after max_samples rows, at the end of the input, or on Ctrl+C.
    """
    rows = []
    started = False
    try:
        for line in lines:
            line = line.strip()
            if line == "BEGIN ACC":
                started, rows = True, []
                print("Found BEGIN ACC, recording ...")
            elif started and line:
                try:
                    n, raw, filt = line.split(",")
                    rows.append((int(n), float(raw), float(filt)))
                except ValueError:
                    print(f"Skipped a bad line: {ascii(line)}")
                    continue
                if len(rows) >= max_samples:
                    break
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C.")
    if not rows:
        raise ValueError("no samples found after 'BEGIN ACC'")
    data = np.array(rows)
    n = data[:, 0].astype(int)
    gaps = np.flatnonzero(np.diff(n) != 1)
    if gaps.size:
        print(f"WARNING: sample index jumps at {gaps.size} place(s), first at n={n[gaps[0]]}."
              " Lines were lost on the UART.")
    return n, data[:, 1], data[:, 2]


def capture(port, baud, max_samples):
    import serial

    def lines():
        with serial.Serial(port, baud, timeout=None) as ser:
            print(f"Listening on {port} at {baud} baud. Press the black RESET button.")
            while True:
                yield ser.readline().decode("ascii", errors="replace")

    return parse_stream(lines(), max_samples)


def save_csv(path, n, raw, filt):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "raw_z_mg", "filtered_z_mg"])
        w.writerows(zip(n, raw, filt))


def load_csv(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0].astype(int), data[:, 1], data[:, 2]


def spectrum_db(signal):
    """One-sided amplitude spectrum in dB, with the mean (gravity) removed."""
    x = signal - signal.mean()
    mag = np.abs(np.fft.rfft(x * np.hanning(len(x)))) * 2 / np.hanning(len(x)).sum()
    freq = np.fft.rfftfreq(len(x), d=1 / FS_HZ)
    return freq, 20 * np.log10(np.maximum(mag, 1e-6))


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


def plot(n, raw, filt, out_stem):
    t = n / FS_HZ
    fig, (ax_t, ax_f) = plt.subplots(2, 1, figsize=(10, 6.4), layout="constrained")

    ax_t.plot(t, raw, color=RAW_COLOR, linewidth=1.2, label="Raw Z")
    ax_t.plot(t, filt, color=FILT_COLOR, linewidth=2, label="Filtered Z (FIR low-pass)")
    ax_t.set_title("Accelerometer Z axis, time domain", loc="left", fontsize=11)
    ax_t.set_xlabel("Time (s)")
    ax_t.set_ylabel("Acceleration (mg)")
    ax_t.set_xlim(t[0], t[-1])
    # Above the axes, in the title row: taps can fill any corner of the plot.
    ax_t.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2,
                frameon=False, labelcolor=INK)
    style(ax_t)

    # Skip the start-up transient (the filter starts from an all-zero state).
    settle = min(len(raw) // 4, 2 * FS_HZ)
    for sig, color, label in ((raw, RAW_COLOR, "Raw Z"), (filt, FILT_COLOR, "Filtered Z")):
        freq, db = spectrum_db(sig[settle:])
        ax_f.plot(freq, db, color=color, linewidth=1.5, label=label)
    ax_f.axvline(CUTOFF_HZ, color=INK_MUTED, linewidth=1, linestyle="--")
    ax_f.text(CUTOFF_HZ + 0.3, ax_f.get_ylim()[1], f"{CUTOFF_HZ} Hz cutoff",
              color=INK_MUTED, fontsize=9, va="top")
    ax_f.set_title("Spectrum (mean removed)", loc="left", fontsize=11)
    ax_f.set_xlabel("Frequency (Hz)")
    ax_f.set_ylabel("Magnitude (dB, mg)")
    ax_f.set_xlim(0, FS_HZ / 2)
    ax_f.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2,
                frameon=False, labelcolor=INK)
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
    src.add_argument("--port", help="serial port of the ST-Link, for example COM3")
    src.add_argument("--csv", type=Path, help="plot a CSV from an earlier capture")
    ap.add_argument("--baud", type=int, default=1_000_000,
                    help="must match USART1 in lab7.ioc (default 1000000)")
    ap.add_argument("--seconds", type=float, default=10,
                    help="recording length; Ctrl+C stops early (default 10)")
    ap.add_argument("--out", type=Path, default=Path("acc_z"),
                    help="output file stem; the script writes .csv, .png and .pdf")
    args = ap.parse_args()

    if args.port:
        n, raw, filt = capture(args.port, args.baud, int(args.seconds * FS_HZ))
        csv_path = args.out.with_suffix(".csv")
        save_csv(csv_path, n, raw, filt)
        print(f"Captured {len(n)} samples ({len(n) / FS_HZ:.1f} s), saved {csv_path}")
    else:
        n, raw, filt = load_csv(args.csv)

    plot(n, raw, filt, args.out)


if __name__ == "__main__":
    main()
