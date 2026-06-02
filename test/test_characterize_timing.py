#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_characterize_timing.py
#
# Loop 108: unit-test the PURE Fmax-search logic in
# post_silicon/characterize_timing.py with a mock (no hardware). Models a chip
# where each decoder has a frequency threshold above which it fails; verifies
# characterize() recovers the chip Fmax, the critical-path decoder, and each
# decoder's max passing frequency.
#
# Run: python3 test/test_characterize_timing.py

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "post_silicon"))

import characterize_timing as ct  # noqa: E402

MHZ = 1_000_000

# Modelled per-decoder Fmax thresholds (passes iff freq <= threshold).
THRESHOLDS = {
    "posit8": 40 * MHZ,   # critical path -- fails first
    "tf32":   80 * MHZ,
    "bf16":   95 * MHZ,
    "nf4":    120 * MHZ,
}
FREQS = [25 * MHZ, 40 * MHZ, 50 * MHZ, 80 * MHZ, 95 * MHZ, 120 * MHZ]


def mock_run(freq_hz):
    return {fmt: freq_hz <= thr for fmt, thr in THRESHOLDS.items()}


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    s = ct.characterize(mock_run, FREQS)

    # All decoders pass only at/below 40 MHz (posit8's threshold) -> chip Fmax = 40 MHz.
    check(s["fmax_all_hz"] == 40 * MHZ,
          f"chip Fmax == 40 MHz (got {s['fmax_all_hz'] and s['fmax_all_hz']/MHZ} MHz)")
    # First failure is at 50 MHz, caused by posit8 (the critical path).
    check(s["first_fail"] == (50 * MHZ, ["posit8"]),
          f"first failure = (50 MHz, [posit8]) (got {s['first_fail']})")
    # Per-decoder Fmax = highest swept freq <= its threshold.
    expect = {"posit8": 40 * MHZ, "tf32": 80 * MHZ, "bf16": 95 * MHZ, "nf4": 120 * MHZ}
    check(s["per_fmt_fmax"] == expect,
          f"per-decoder Fmax correct (got {s['per_fmt_fmax']})")

    # report() renders without error and names the critical path.
    r = ct.report(s)
    check("critical path" in r and "posit8" in r, "report() names the critical path")

    # Degenerate: a decoder that fails at every swept freq -> Fmax None.
    s2 = ct.characterize(lambda f: {"x": False}, [25 * MHZ, 40 * MHZ])
    check(s2["per_fmt_fmax"]["x"] is None and s2["fmax_all_hz"] is None,
          "decoder failing at all freqs -> Fmax None")

    # --- Deterministic protocol latency (cycles) -----------------------------
    # 1-byte decode: CMD(2) + data(1) + 1 = 4 to first result; +4 -> 7 full.
    check(ct.protocol_latency(1) == {"to_first_result": 4, "to_full_result": 7},
          f"1-byte latency = 4/7 cycles (got {ct.protocol_latency(1)})")
    check(ct.protocol_latency(2)["to_full_result"] == 8, "bf16 (2-byte) full = 8 cycles")
    check(ct.protocol_latency(3)["to_full_result"] == 9, "tf32 (3-byte) full = 9 cycles")

    # latency_table derived from the generated vectors' input byte counts.
    sys.path.insert(0, os.path.join(ROOT, "post_silicon"))
    import corona_vectors as cv
    BYTES = {}
    NAMES = {"FP8_E5M2_VECTORS": "fp8_e5m2", "BF16_VECTORS": "bf16",
             "POSIT8_VECTORS": "posit8", "INT8_VECTORS": "int8", "TF32_VECTORS": "tf32",
             "MXFP8_E4M3_VECTORS": "mxfp8_e4m3", "LNS8_VECTORS": "lns8",
             "BCD_VECTORS": "bcd", "FP4_E2M1_VECTORS": "fp4", "NF4_VECTORS": "nf4",
             "FP6_E3M2_VECTORS": "fp6_e3m2", "FP6_E2M3_VECTORS": "fp6_e2m3",
             "E8M0_VECTORS": "e8m0", "MXINT8_VECTORS": "mxint8",
             "E4M3_FNUZ_VECTORS": "fp8_e4m3_fnuz", "INT4_VECTORS": "int4",
             "BITNET_VECTORS": "bitnet"}
    for var, dec in NAMES.items():
        inp = getattr(cv, var)[0][0]
        BYTES[dec] = len(inp) if isinstance(inp, list) else 1
    table = ct.latency_table(BYTES)
    check(len(table) == 17, f"latency table covers 17 decoders (got {len(table)})")
    check(table["tf32"]["to_full_result"] == 9 and table["bf16"]["to_full_result"] == 8
          and table["posit8"]["to_full_result"] == 7,
          "latency table matches byte counts (tf32=9, bf16=8, 1-byte=7)")

    print("\n" + "=" * 60)
    if errors:
        print(f"characterize_timing: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: Fmax search logic correct (chip Fmax, critical path, per-decoder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
