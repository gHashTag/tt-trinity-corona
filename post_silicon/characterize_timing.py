# SPDX-License-Identifier: Apache-2.0
# post_silicon/characterize_timing.py
#
# Loop 108: post-silicon Fmax timing characterization (Phase G prep).
#
# Corona is one clock domain, so "timing characterization" on the RP2350
# demoboard means: sweep the project clock UPWARD and find the frequency at which
# each decoder first produces a wrong result. The lowest such frequency is the
# chip Fmax (the critical path); the decoder that fails there is the critical-path
# decoder. This is the first published GF180MCU timing data for these combinational
# format converters (carried from Loop 77 Option B).
#
# Structure:
#   * characterize(run_vectors_at, freqs_hz) -- PURE search logic, no hardware;
#     fully unit-tested in test/test_characterize_timing.py.
#   * make_runner(drv, set_freq_hz, vectors_by_fmt) -- the hardware wiring; takes a
#     `set_freq_hz(hz)` callback (demoboard-firmware specific, supplied at bring-up)
#     and returns a run_vectors_at(freq) -> {fmt: all_passed}.
#
# Until silicon arrives (~Nov 2026) only the pure search logic runs; the hardware
# runner is a documented hook. Pure stdlib (MicroPython-compatible).


def characterize(run_vectors_at, freqs_hz):
    """Sweep ascending `freqs_hz`; at each, `run_vectors_at(freq)` returns
    {fmt_label: all_vectors_passed(bool)}. Returns a summary:

        {
          "fmax_all_hz":  highest freq where EVERY format passed (or None),
          "first_fail":   (freq_hz, [fmt,...]) -- lowest freq with any failure,
          "per_fmt_fmax": {fmt: highest freq it passed (or None)},
          "swept_hz":     [freqs in order],
        }

    Higher freq -> more failures (monotonic) is expected but not assumed: each
    format's recorded Fmax is simply the highest swept freq at which it passed."""
    freqs = list(freqs_hz)
    per_fmt_fmax = {}
    fmax_all = None
    first_fail = None
    for freq in freqs:
        results = run_vectors_at(freq)
        failed = sorted(f for f, ok in results.items() if not ok)
        for fmt, ok in results.items():
            if ok and (per_fmt_fmax.get(fmt) is None or freq > per_fmt_fmax[fmt]):
                per_fmt_fmax[fmt] = freq
            per_fmt_fmax.setdefault(fmt, None)
        if not failed:
            if fmax_all is None or freq > fmax_all:
                fmax_all = freq
        elif first_fail is None:
            first_fail = (freq, failed)
    return {
        "fmax_all_hz": fmax_all,
        "first_fail": first_fail,
        "per_fmt_fmax": per_fmt_fmax,
        "swept_hz": freqs,
    }


def make_runner(drv, set_freq_hz, vectors_by_fmt):
    """Wire a hardware run_vectors_at for the demoboard.

    drv             -- a CoronaDriver (test_corona.CoronaDriver).
    set_freq_hz(hz) -- demoboard-firmware callback to set the project clock; the
                       exact API is board-specific and supplied at bring-up.
    vectors_by_fmt  -- {fmt_label: (fmt_id, [(input_bytes, expected_fp32), ...])}.
    """
    from test_corona import bytes_to_u32  # noqa: E402  (demoboard import)

    def run_vectors_at(freq_hz):
        set_freq_hz(freq_hz)
        out = {}
        for fmt, (fmt_id, vectors) in vectors_by_fmt.items():
            ok = True
            drv.reset()
            for data, expected in vectors:
                data = [data] if isinstance(data, int) else data
                got = bytes_to_u32(drv.decode(fmt_id, data))
                if got != expected:
                    ok = False
                    break
            out[fmt] = ok
        return out

    return run_vectors_at


def report(summary):
    """Human-readable summary (for the USB-serial bring-up log)."""
    lines = []
    fa = summary["fmax_all_hz"]
    lines.append("Fmax (all decoders pass): "
                 + (f"{fa/1e6:.2f} MHz" if fa else "n/a"))
    ff = summary["first_fail"]
    if ff:
        lines.append(f"critical path: first failure at {ff[0]/1e6:.2f} MHz "
                     f"in {', '.join(ff[1])}")
    for fmt in sorted(summary["per_fmt_fmax"]):
        hz = summary["per_fmt_fmax"][fmt]
        lines.append(f"  {fmt:14s} Fmax = "
                     + (f"{hz/1e6:.2f} MHz" if hz else "FAILED at all swept freqs"))
    return "\n".join(lines)


if __name__ == "__main__":
    print("characterize_timing: pure logic module. On the demoboard, supply a "
          "set_freq_hz() hook and vectors, build a runner via make_runner(), then "
          "call characterize(runner, freqs_hz). See test/test_characterize_timing.py "
          "for the search-logic tests.")
