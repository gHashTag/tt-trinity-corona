#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Reproducible check for the bitnet_encoder neuron_base-width bug (loop 128).
# ternary_dot's `neuron_base` is [9:0] (10-bit) but Layer 1 calls it with k*64 for
# k=0..31 (up to 1984), so neuron_base truncates mod 1024 and neurons 16..31 alias
# 0..15 (h1[k]==h1[k-16]); the 64->32->8 demo realizes only 16 distinct neurons.
# Reads the param width from the RTL so it doubles as a regression check.
import os, re, sys

DIES = {
    "gamma": "/Users/playra/tt-trinity-gamma/src/bitnet_encoder.v",
    "euler": "/Users/playra/tt-trinity-euler/src/bitnet_encoder.v",
}

def neuron_base_width(path):
    txt = open(path).read()
    m = re.search(r"input\s*\[(\d+):0\]\s*neuron_base", txt)
    return int(m.group(1)) + 1 if m else None

def main():
    aliases = sum(1 for k in range(16, 32) if ((k * 64) & 0x3FF) == (((k - 16) * 64) & 0x3FF))
    print(f"neuron_base collision: {aliases}/16 upper neurons alias a lower one "
          f"(h1[k]==h1[k-16]); 32 nominal -> {32 - aliases} distinct\n")
    bad = False
    for die, path in DIES.items():
        if not os.path.exists(path):
            print(f"  {die}: (no bitnet_encoder.v)"); continue
        w = neuron_base_width(path)
        needed = (31 * 64).bit_length()        # 11 bits to hold 1984
        ok = w is not None and w >= needed
        print(f"  {die}: neuron_base is {w}-bit (needs >= {needed}) -> "
              f"{'OK (fixed)' if ok else 'BUG: aliasing'}")
        bad = bad or not ok
    print("\nNote: bitnet_encoder is a synthetic-weight demo, so this does not corrupt a")
    print("trained model; it is a latent architectural defect on Gamma/Euler silicon.")
    print("Fix = widen neuron_base (and w_gen addr) to 11 bits; frozen die left as-is.")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
