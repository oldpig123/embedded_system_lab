"""Receive raw and FIR-filtered accelerometer data over Wi-Fi and plot it live.

The board connects to this program as a TCP client. It sends one line per
sample, usually in blocks of 25 lines:

    <n>,<raw_z>,<filtered_z>\\n

n is the board's sample index (50 Hz), so the time axis is n / 50 s. The
board can also send comment lines that start with "#", for example
"# dropped=0". The program prints them and does not plot them.

When the window closes (or --duration ends), the program writes a CSV in the
plot_acc.py format. Use plot_acc.py --csv to make the static figure.

Usage:
    uv run wifi_plot.py                          # live window on port 8002
    uv run wifi_plot.py --duration 20            # no window, run 20 s, save
    uv run plot_acc.py --csv wifi_acc_z.csv --out wifi_acc_z   # static figure
"""

import argparse
import socket
import threading
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from plot_acc import FILT_COLOR, FS_HZ, INK, RAW_COLOR, save_csv, style


class Receiver:
    """Accept board connections on a background thread and store samples."""

    def __init__(self, host, port):
        self.rows = []          # (n, raw, filt) of the current connection
        self.peer = None
        self.gaps = 0
        self.bad_lines = 0
        self.lock = threading.Lock()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((host, port))
        self._server.listen(1)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            conn, addr = self._server.accept()
            self.peer = "%s:%d" % addr
            with self.lock:
                # A new connection means the board was reset and n starts at 0
                # again. Keep only the newest run, so n stays continuous.
                if self.rows:
                    print(f"New connection: dropped {len(self.rows)} samples of the old run.")
                self.rows, self.gaps, self.bad_lines = [], 0, 0
            print("Connected:", self.peer)
            try:
                self._read(conn)
            except OSError as e:
                print("Connection error:", e)
            finally:
                conn.close()
                print("Disconnected:", self.peer)
                self.peer = None

    def _read(self, conn):
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
            # TCP is a byte stream. One recv can hold half a line or many lines.
            *lines, buf = buf.split(b"\n")
            for line in lines:
                self._parse(line.decode("ascii", "replace").strip())

    def _parse(self, line):
        if not line:
            return
        if line.startswith("#"):
            print("Board:", line)
            return
        try:
            n, raw, filt = line.split(",")
            row = (int(n), float(raw), float(filt))
        except ValueError:
            self.bad_lines += 1
            print(f"Skipped a bad line: {ascii(line)}")
            return
        with self.lock:
            if self.rows and row[0] != self.rows[-1][0] + 1:
                self.gaps += 1
                print(f"WARNING: sample index jumps from {self.rows[-1][0]} to {row[0]}.")
            self.rows.append(row)

    def snapshot(self):
        with self.lock:
            return list(self.rows), self.gaps, self.bad_lines


def build_figure():
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    (raw_line,) = ax.plot([], [], color=RAW_COLOR, linewidth=1.2, label="Raw Z (before filter)")
    (filt_line,) = ax.plot([], [], color=FILT_COLOR, linewidth=2,
                           label="Filtered Z (after FIR low-pass)")
    ax.set_xlabel("Board time n / 50 Hz (s)")
    ax.set_ylabel("Acceleration (mg)")
    ax.set_title("Waiting for the board ...", loc="left", fontsize=11)
    ax.legend(loc="upper right", frameon=False, labelcolor=INK)
    style(ax)
    return fig, ax, raw_line, filt_line


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="0.0.0.0", help="address to listen on (default all)")
    ap.add_argument("--port", type=int, default=8002, help="TCP port (default 8002)")
    ap.add_argument("--window", type=float, default=10.0, help="seconds shown (default 10)")
    ap.add_argument("--duration", type=float,
                    help="run N seconds with no window, then save and exit")
    ap.add_argument("--out", type=Path, default=Path("wifi_acc_z"),
                    help="output file stem; the program writes .csv (and .png)")
    args = ap.parse_args()

    if args.duration is not None:
        plt.switch_backend("Agg")

    rx = Receiver(args.host, args.port)
    fig, ax, raw_line, filt_line = build_figure()
    print(f"Listening on {args.host}:{args.port}. Reset the board after this starts.")

    def update(_frame=None):
        rows, gaps, bad = rx.snapshot()
        state = f"Connected: {rx.peer}" if rx.peer else "Waiting for the board ..."
        if rows:
            data = np.array(rows)
            t = data[:, 0] / FS_HZ
            raw_line.set_data(t, data[:, 1])
            filt_line.set_data(t, data[:, 2])
            ax.set_xlim(max(t[0], t[-1] - args.window), max(t[-1], t[0] + args.window))
            shown = t >= ax.get_xlim()[0]
            lo = min(data[shown, 1].min(), data[shown, 2].min())
            hi = max(data[shown, 1].max(), data[shown, 2].max())
            pad = max(20.0, 0.05 * (hi - lo))
            ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(f"{state}  |  samples: {len(rows)}  |  index gaps: {gaps}"
                     f"  |  bad lines: {bad}", loc="left", fontsize=11)
        return raw_line, filt_line

    if args.duration is None:
        _anim = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
        plt.show()
    else:
        time.sleep(args.duration)
        update()

    rows, gaps, bad = rx.snapshot()
    print(f"Samples: {len(rows)}, index gaps: {gaps}, bad lines: {bad}")
    if not rows:
        print("No samples received, so no files were written.")
        return
    n, raw, filt = (np.array(col) for col in zip(*rows))
    csv_path = args.out.with_suffix(".csv")
    save_csv(csv_path, n, raw, filt)
    print(f"Saved {csv_path}")
    if args.duration is not None:
        png_path = args.out.with_suffix(".png")
        fig.savefig(png_path, dpi=200)
        print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
