# SPDX-License-Identifier: Apache-2.0
# post_silicon/boot_corona.py -- RP2350 demoboard auto-boot for TRI-1 Corona
#
# Copy this file to the demoboard as boot.py or main.py.
# On power-up, it enables Corona and runs the quick test suite.
# Results are printed to USB serial (115200 baud).
#
# Usage:
#   1. Copy test_corona.py and boot_corona.py to demoboard filesystem
#   2. Rename boot_corona.py -> main.py (or boot.py)
#   3. Power cycle the demoboard
#   4. Connect via serial terminal to see results

import time

try:
    from machine import Pin
    HAS_MACHINE = True
except ImportError:
    HAS_MACHINE = False


def main():
    print("\n" + "=" * 40)
    print("TRI-1 Corona -- Post-Silicon Validation")
    print("=" * 40)

    try:
        from ttboard.demoboard import DemoBoard
        tt = DemoBoard.get()
    except ImportError:
        print("ERROR: ttboard not available.")
        print("This script must run on the TT RP2350 demoboard.")
        return

    print("Enabling tt_um_trinity_corona...")
    try:
        tt.shuttle.tt_um_trinity_corona.enable()
    except Exception as e:
        print(f"ERROR enabling project: {e}")
        return

    time.sleep(0.1)

    import test_corona

    print("\n--- Quick Tests (23 tests) ---\n")
    ok = test_corona.run_all(tt)

    if ok:
        print("\n>>> SILICON VALIDATION: ALL PASS <<<")
    else:
        print("\n>>> SILICON VALIDATION: FAILURES DETECTED <<<")

    print("\nTo run exhaustive sweeps (68k+ values):")
    print("  import test_corona")
    print("  test_corona.run_exhaustive()")


main()
