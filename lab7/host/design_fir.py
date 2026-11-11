"""Design a low-pass FIR filter and print its coefficients as a C array.

This script does the same job as MATLAB fir1() in the lecture slides:
a windowed-sinc design with a Hamming window, scaled to a DC gain of 1.

Usage:
    uv run design_fir.py                              # 29 taps, 5 Hz cutoff, fs = 50 Hz
    uv run design_fir.py --taps 29 --cutoff 6000 --fs 48000 \
        --name firCoeffs32 --taps-macro NUM_TAPS              # the arm_fir_example filter
"""

import argparse

import numpy as np
from scipy import signal


def design(taps, cutoff_hz, fs_hz):
    return signal.firwin(taps, cutoff_hz, fs=fs_hz, window="hamming")


def to_c_array(h, name, taps_macro, per_line=8):
    # CMSIS arm_fir_f32 wants the coefficients in time-reversed order (slide 15).
    h = h[::-1]
    values = [f"{v:+.10f}f" for v in h]
    lines = [", ".join(values[i:i + per_line]) for i in range(0, len(values), per_line)]
    body = ",\n  ".join(lines)
    return f"const float32_t {name}[{taps_macro}] = {{\n  {body}\n}};"


def gain_db(h, freq_hz, fs_hz):
    _, resp = signal.freqz(h, worN=[freq_hz], fs=fs_hz)
    return 20 * np.log10(np.abs(resp[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taps", type=int, default=29, help="filter length (NUM_TAPS)")
    ap.add_argument("--cutoff", type=float, default=5.0, help="cutoff frequency in Hz")
    ap.add_argument("--fs", type=float, default=50.0, help="sample rate in Hz")
    ap.add_argument("--name", default="accCoeffs", help="C array name (default accCoeffs)")
    ap.add_argument("--taps-macro", default="ACC_NUM_TAPS",
                    help="C macro for the filter length (default ACC_NUM_TAPS)")
    args = ap.parse_args()

    h = design(args.taps, args.cutoff, args.fs)

    print(f"/* Low-pass FIR: {args.taps} taps, cutoff {args.cutoff:g} Hz, fs {args.fs:g} Hz,")
    print(f"   Hamming window. Group delay = {(args.taps - 1) / 2:g} samples"
          f" = {(args.taps - 1) / 2 / args.fs * 1000:g} ms. */")
    print(f"#define {args.taps_macro} {args.taps}")
    print(to_c_array(h, args.name, args.taps_macro))
    print()
    print("/* Gain check:")
    for f in (0.0, args.cutoff, 2 * args.cutoff):
        print(f"   {f:>10g} Hz : {gain_db(h, f, args.fs):7.2f} dB")
    print("*/")


if __name__ == "__main__":
    main()
