#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# tools/ssot_layout.py
#
# Loop 80: the ONE machine-readable reader of the Corona ROM layout SSOT.
#
# Before this module the 80-bit field layout existed as literal bit-shifts in
# THREE hand-maintained places (rom_layout.t27, gen_rom.py pack_record,
# test_rom_spec_crosscheck.py extract_fields). Loop 79 added a cross-check that
# proved they agreed; Loop 80 removes one of the copies entirely: every consumer
# that needs to extract a field from a packed ROM word now derives the bit
# position from `rom_layout.t27` via this module, so there is exactly ONE
# layout source for the test/tooling side (plus gen_rom's packer, which the
# Loop 79 cross-check pins to the same SSOT).
#
# Pure stdlib. No side effects on import beyond reading the repo's spec files.

import os
import re

_DIR = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(_DIR, "..", "specs", "corona")
ROM_LAYOUT = os.path.join(SPECS, "rom_layout.t27")
ORACLE = os.path.join(SPECS, "corona_oracle.t27")


def read(path):
    with open(path, errors="replace") as f:
        return f.read()


def field_offsets(text=None):
    """Parse `FIELD_NAME = struct { hi: u8=H, lo: u8=L, width: u8=W }` from
    rom_layout.t27. Returns {NAME: (hi, lo, width)}."""
    if text is None:
        text = read(ROM_LAYOUT)
    pat = re.compile(
        r"FIELD_(\w+)\s*=\s*struct\s*\{\s*"
        r"hi\s*:\s*u8\s*=\s*(\d+)\s*,\s*"
        r"lo\s*:\s*u8\s*=\s*(\d+)\s*,\s*"
        r"width\s*:\s*u8\s*=\s*(\d+)\s*\}")
    return {name: (int(hi), int(lo), int(w))
            for name, hi, lo, w in pat.findall(text)}


def const_enum(text, prefix):
    """Parse `pub const PREFIX_NAME : uN = VALUE;` (decimal or 0x hex).
    Returns {NAME: int}."""
    pat = re.compile(
        rf"pub\s+const\s+{prefix}_(\w+)\s*:\s*u\d+\s*=\s*(0[xX][0-9a-fA-F]+|\d+)")
    return {name: int(val, 0) for name, val in pat.findall(text)}


def cluster_counts(text=None):
    if text is None:
        text = read(ORACLE)
    m = re.search(r"CLUSTER_COUNTS\s*=\s*struct\s*\{(.*?)\}", text, re.DOTALL)
    if not m:
        return {}
    return {n: int(v) for n, v in re.findall(r"(\w+)\s*:\s*u8\s*=\s*(\d+)", m.group(1))}


def scalar(name, text=None, path=ROM_LAYOUT):
    if text is None:
        text = read(path)
    m = re.search(rf"pub\s+const\s+{name}\s*:\s*u\d+\s*=\s*(\d+)", text)
    return int(m.group(1)) if m else None


# Cached canonical layout (read once from the SSOT).
LAYOUT = field_offsets()


def extract(word, field_name, layout=None):
    """Extract FIELD_<field_name> from a packed 80-bit ROM word using the
    SSOT-declared (lo, width). `field_name` is the suffix after FIELD_, e.g.
    'TOTAL_BITS', 'SIGN_BITS', 'FORMAT_INDEX_ID'."""
    lo_map = LAYOUT if layout is None else layout
    if field_name not in lo_map:
        raise KeyError(f"unknown SSOT field FIELD_{field_name}; "
                       f"known: {sorted(lo_map)}")
    _hi, lo, width = lo_map[field_name]
    return (word >> lo) & ((1 << width) - 1)


if __name__ == "__main__":
    print(f"rom_layout.t27 fields ({len(LAYOUT)}):")
    for name, (hi, lo, w) in sorted(LAYOUT.items(), key=lambda kv: -kv[1][0]):
        print(f"  FIELD_{name:<16} [{hi:>2}:{lo:>2}] width {w}")
    print(f"RECORD_BITS = {scalar('RECORD_BITS')}, "
          f"RECORD_COUNT = {scalar('RECORD_COUNT')}, "
          f"TOTAL_FORMATS = {scalar('TOTAL_FORMATS', path=ORACLE)}")
