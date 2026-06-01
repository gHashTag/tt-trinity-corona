#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# tools/gen_rom.py -- Generate format_rom.v from SSOT catalog data.
# Packs 80 records x 80 bits per specs/corona/rom_layout.t27.
#
# ROM layout (80 bits per record):
#   [79:72] format_index_id  (8 bits)
#   [71:68] cluster_id       (4 bits)
#   [67:64] status_id        (4 bits)
#   [63:56] total_bits       (8 bits)
#   [55:52] sign_bits        (4 bits)
#   [51:44] exp_bits         (8 bits)
#   [43:36] mant_bits        (8 bits)
#   [35:32] encoding_kind    (4 bits)
#   [31:16] phi_distance_q16 (16 bits)
#   [15:8]  ref_index        (8 bits)
#   [7:0]   flags            (8 bits)

import sys
import os
import math

# Encoding kinds (from rom_layout.t27)
ENC_FP = 0
ENC_POSIT = 1
ENC_LNS = 2
ENC_INT = 3
ENC_BCD = 4
ENC_MX = 5
ENC_TAKUM = 6
ENC_GF = 7
ENC_HISTORICAL = 8
ENC_THEORETICAL = 9

# Claim-status IDs (from corona_oracle.t27)
ST_VERIFIED = 0
ST_EMPIRICAL = 1
ST_CONJECTURE = 2
ST_RISK = 3
ST_RETRACTED = 4
ST_EXPERIMENTAL = 5
ST_HISTORICAL = 6
ST_SPEC = 7

# Cluster IDs (0-12, from corona_oracle.t27 Section 4)
CL_IEEE_BIN = 0
CL_IEEE_DEC = 1
CL_ML_LOW = 2
CL_GOLDENFLOAT = 3
CL_POSIT = 4
CL_OCP_MX = 5
CL_LNS = 6
CL_INT_FIXED = 7
CL_HISTORICAL = 8
CL_THEORETICAL = 9
CL_COMPRESSION = 10
CL_EXTENDED = 11
CL_QUANT = 12

# Flags
FLAG_ON_DIE = 0x01
FLAG_GAMMA = 0x02
FLAG_D2D = 0x04
FLAG_EXPERIMENTAL = 0x08


def phi_distance(exp_bits, mant_bits):
    """Compute Q16 phi-distance: how close exp/mant ratio is to 1/phi."""
    if mant_bits == 0:
        return 0xFFFF
    ratio = exp_bits / mant_bits
    phi_inv = (math.sqrt(5) - 1) / 2  # ~0.618
    dist = abs(ratio - phi_inv)
    q16 = int(min(dist * 65536, 65535))
    return q16


def pack_record(fmt_id, cluster, status, total_bits, sign_bits,
                exp_bits, mant_bits, enc_kind, ref_idx, flags):
    """Pack a single 80-bit record per rom_layout.t27.
    NOTE: total_bits is 8-bit; 256 wraps to 0 (fmt_id 4=fp256, 29=GF256)."""
    if total_bits > 255:
        import sys
        print(f"WARNING: fmt_id={fmt_id} total_bits={total_bits} truncated to "
              f"{total_bits & 0xFF} (8-bit field overflow)", file=sys.stderr)
    phi_q16 = phi_distance(exp_bits, mant_bits)
    word = 0
    word |= (fmt_id & 0xFF) << 72
    word |= (cluster & 0xF) << 68
    word |= (status & 0xF) << 64
    word |= (total_bits & 0xFF) << 56
    word |= (sign_bits & 0xF) << 52
    word |= (exp_bits & 0xFF) << 44
    word |= (mant_bits & 0xFF) << 36
    word |= (enc_kind & 0xF) << 32
    word |= (phi_q16 & 0xFFFF) << 16
    word |= (ref_idx & 0xFF) << 8
    word |= (flags & 0xFF)
    return word


# 80 format records, ordered by format_index_id (0-79).
# Fields: (fmt_id, cluster, status, total_bits, sign, exp, mant, enc_kind, ref_idx, flags)
CATALOG = [
    # Cluster 0: IEEE 754 binary (5)
    (0,  CL_IEEE_BIN, ST_SPEC,       16,  1,  5, 10, ENC_FP, 0, 0),           # fp16
    (1,  CL_IEEE_BIN, ST_SPEC,       32,  1,  8, 23, ENC_FP, 1, 0),           # fp32
    (2,  CL_IEEE_BIN, ST_SPEC,       64,  1, 11, 52, ENC_FP, 2, 0),           # fp64
    (3,  CL_IEEE_BIN, ST_SPEC,      128,  1, 15,112, ENC_FP, 3, 0),           # fp128
    (4,  CL_IEEE_BIN, ST_SPEC,      256,  1, 19,236, ENC_FP, 4, 0),           # fp256

    # Cluster 1: IEEE 754 decimal (3)
    (5,  CL_IEEE_DEC, ST_SPEC,       32,  1,  8, 20, ENC_BCD, 5, 0),          # decimal32
    (6,  CL_IEEE_DEC, ST_SPEC,       64,  1,  8, 50, ENC_BCD, 6, 0),          # decimal64
    (7,  CL_IEEE_DEC, ST_SPEC,      128,  1,  8,110, ENC_BCD, 7, 0),          # decimal128

    # Cluster 2: ML low-precision (7)
    (8,  CL_ML_LOW,   ST_SPEC,       16,  1,  8,  7, ENC_FP, 8, FLAG_ON_DIE), # bf16
    (9,  CL_ML_LOW,   ST_SPEC,       32,  1,  8, 10, ENC_FP, 9, FLAG_ON_DIE), # tf32
    (10, CL_ML_LOW,   ST_EXPERIMENTAL,8,  1,  5,  2, ENC_FP,10, FLAG_ON_DIE), # fp8 e5m2
    (11, CL_ML_LOW,   ST_EXPERIMENTAL,8,  1,  4,  3, ENC_FP,11, FLAG_ON_DIE), # fp8 e4m3
    (12, CL_ML_LOW,   ST_SPEC,        6,  1,  3,  2, ENC_FP,12, FLAG_ON_DIE), # fp6 e3m2
    (13, CL_ML_LOW,   ST_SPEC,        4,  1,  2,  1, ENC_FP,13, FLAG_ON_DIE), # fp4 e2m1
    (14, CL_ML_LOW,   ST_EXPERIMENTAL,8,  1,  4,  3, ENC_FP,14, FLAG_ON_DIE), # fp8 e4m3 fnuz

    # Cluster 3: GoldenFloat (16)
    (15, CL_GOLDENFLOAT, ST_CONJECTURE, 4, 1, 1, 2, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF4
    (16, CL_GOLDENFLOAT, ST_CONJECTURE, 6, 1, 2, 3, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF6
    (17, CL_GOLDENFLOAT, ST_CONJECTURE, 8, 1, 3, 4, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF8
    (18, CL_GOLDENFLOAT, ST_CONJECTURE,10, 1, 3, 6, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF10
    (19, CL_GOLDENFLOAT, ST_CONJECTURE,12, 1, 4, 7, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF12
    (20, CL_GOLDENFLOAT, ST_CONJECTURE,14, 1, 5, 8, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF14
    (21, CL_GOLDENFLOAT, ST_CONJECTURE,16, 1, 5,10, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF16
    (22, CL_GOLDENFLOAT, ST_CONJECTURE,20, 1, 7,12, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF20
    (23, CL_GOLDENFLOAT, ST_CONJECTURE,24, 1, 8,15, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF24
    (24, CL_GOLDENFLOAT, ST_CONJECTURE,32, 1,11,20, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF32
    (25, CL_GOLDENFLOAT, ST_CONJECTURE,48, 1,16,31, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF48
    (26, CL_GOLDENFLOAT, ST_CONJECTURE,64, 1,22,41, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF64
    (27, CL_GOLDENFLOAT, ST_CONJECTURE,96, 1,33,62, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF96
    (28, CL_GOLDENFLOAT, ST_CONJECTURE,128,1,44,83, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF128
    (29, CL_GOLDENFLOAT, ST_CONJECTURE,256,1,88,167,ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GF256
    (30, CL_GOLDENFLOAT, ST_CONJECTURE, 2, 1, 0, 1, ENC_GF,15, FLAG_GAMMA|FLAG_D2D),  # GFTernary

    # Cluster 4: Posit / Unum III (8)
    (31, CL_POSIT, ST_EXPERIMENTAL, 8,  1, 0, 0, ENC_POSIT,16, FLAG_ON_DIE),  # posit8 es=0
    (32, CL_POSIT, ST_EXPERIMENTAL,16,  1, 1, 0, ENC_POSIT,16, FLAG_GAMMA|FLAG_D2D),  # posit16
    (33, CL_POSIT, ST_EXPERIMENTAL,32,  1, 2, 0, ENC_POSIT,17, 0),            # posit32
    (34, CL_POSIT, ST_EXPERIMENTAL,64,  1, 3, 0, ENC_POSIT,17, 0),            # posit64
    (35, CL_POSIT, ST_EXPERIMENTAL, 8,  1, 0, 0, ENC_TAKUM,18, FLAG_EXPERIMENTAL),  # takum8
    (36, CL_POSIT, ST_EXPERIMENTAL,16,  1, 0, 0, ENC_TAKUM,18, FLAG_EXPERIMENTAL),  # takum16
    (37, CL_POSIT, ST_EXPERIMENTAL,32,  1, 0, 0, ENC_TAKUM,18, FLAG_EXPERIMENTAL),  # takum32
    (38, CL_POSIT, ST_EXPERIMENTAL,64,  1, 0, 0, ENC_TAKUM,18, FLAG_EXPERIMENTAL),  # takum64

    # Cluster 5: OCP MX (3)
    (39, CL_OCP_MX, ST_SPEC,  8, 1, 4, 3, ENC_MX, 19, FLAG_ON_DIE),  # MXFP8 E4M3
    (40, CL_OCP_MX, ST_SPEC,  6, 1, 3, 2, ENC_MX, 19, FLAG_ON_DIE),  # MXFP6 E3M2
    (41, CL_OCP_MX, ST_SPEC,  4, 1, 2, 1, ENC_MX, 19, FLAG_ON_DIE),  # MXFP4 E2M1

    # Cluster 6: LNS (4)
    (42, CL_LNS, ST_EXPERIMENTAL,  8, 1, 3, 4, ENC_LNS, 20, FLAG_ON_DIE),  # LNS8
    (43, CL_LNS, ST_EXPERIMENTAL, 16, 1, 5,10, ENC_LNS, 20, 0),            # LNS16
    (44, CL_LNS, ST_EXPERIMENTAL, 32, 1, 8,23, ENC_LNS, 21, 0),            # LNS32
    (45, CL_LNS, ST_EXPERIMENTAL, 32, 1, 8,23, ENC_LNS, 22, 0),            # Coleman LNS32

    # Cluster 7: Integer/fixed (8)
    (46, CL_INT_FIXED, ST_SPEC,  4, 1, 0, 3, ENC_INT, 23, FLAG_ON_DIE|FLAG_GAMMA|FLAG_D2D),  # int4
    (47, CL_INT_FIXED, ST_SPEC,  8, 1, 0, 7, ENC_INT, 23, FLAG_ON_DIE|FLAG_GAMMA|FLAG_D2D),  # int8
    (48, CL_INT_FIXED, ST_SPEC, 16, 1, 0,15, ENC_INT, 23, 0),                    # int16
    (49, CL_INT_FIXED, ST_SPEC, 32, 1, 0,31, ENC_INT, 23, 0),                    # int32
    (50, CL_INT_FIXED, ST_SPEC, 64, 1, 0,63, ENC_INT, 23, 0),                    # int64
    (51, CL_INT_FIXED, ST_SPEC,  4, 0, 0, 4, ENC_INT, 24, 0),                    # q4 (fixed)
    (52, CL_INT_FIXED, ST_SPEC, 16, 1, 0,15, ENC_INT, 24, 0),                    # q15 (fixed)
    (53, CL_INT_FIXED, ST_SPEC,  8, 0, 0, 8, ENC_BCD, 25, FLAG_ON_DIE),          # bcd (packed)

    # Cluster 8: Historical/vendor (10)
    (54, CL_HISTORICAL, ST_HISTORICAL, 32, 1, 8,23, ENC_HISTORICAL, 26, 0),  # VAX F
    (55, CL_HISTORICAL, ST_HISTORICAL, 64, 1, 8,55, ENC_HISTORICAL, 26, 0),  # VAX D
    (56, CL_HISTORICAL, ST_HISTORICAL, 32, 1, 7,24, ENC_HISTORICAL, 27, 0),  # IBM HFP32
    (57, CL_HISTORICAL, ST_HISTORICAL, 64, 1, 7,56, ENC_HISTORICAL, 27, 0),  # IBM HFP64
    (58, CL_HISTORICAL, ST_HISTORICAL, 64, 1,15,48, ENC_HISTORICAL, 28, 0),  # Cray float
    (59, CL_HISTORICAL, ST_HISTORICAL, 32, 1, 8,23, ENC_HISTORICAL, 29, 0),  # Microsoft MBF32
    (60, CL_HISTORICAL, ST_HISTORICAL, 64, 1, 8,55, ENC_HISTORICAL, 29, 0),  # Microsoft MBF64
    (61, CL_HISTORICAL, ST_HISTORICAL, 32, 1, 8,23, ENC_HISTORICAL, 30, 0),  # PDP-11 float
    (62, CL_HISTORICAL, ST_HISTORICAL, 80, 1,15,64, ENC_HISTORICAL, 31, 0),  # x87 extended
    (63, CL_HISTORICAL, ST_HISTORICAL, 48, 1, 8,39, ENC_HISTORICAL, 32, 0),  # x87 48-bit

    # Cluster 9: Theoretical (4)
    (64, CL_THEORETICAL, ST_SPEC,       32, 1, 0, 0, ENC_THEORETICAL, 33, 0),  # unum I
    (65, CL_THEORETICAL, ST_SPEC,       32, 1, 0, 0, ENC_THEORETICAL, 34, 0),  # unum II (SORNs)
    (66, CL_THEORETICAL, ST_CONJECTURE, 32, 1, 8,23, ENC_THEORETICAL, 35, 0),  # AFP
    (67, CL_THEORETICAL, ST_CONJECTURE, 32, 1, 8,23, ENC_THEORETICAL, 36, 0),  # Q-MX

    # Cluster 10: Compression (4)
    (68, CL_COMPRESSION, ST_SPEC,        16, 1, 5,10, ENC_FP, 37, 0),           # fp16 e5m10 alt
    (69, CL_COMPRESSION, ST_EXPERIMENTAL, 8, 1, 4, 3, ENC_FP, 38, FLAG_ON_DIE), # fp8 e4m3 fnuz-alt
    (70, CL_COMPRESSION, ST_EXPERIMENTAL, 4, 0, 0, 4, ENC_INT,39, FLAG_ON_DIE), # nf4 (QLoRA)
    (71, CL_COMPRESSION, ST_EXPERIMENTAL, 2, 1, 0, 1, ENC_INT,40, FLAG_ON_DIE|FLAG_GAMMA|FLAG_D2D),  # bitnet

    # Cluster 11: Extended (3)
    (72, CL_EXTENDED, ST_SPEC,      128, 1,15,112, ENC_FP, 41, 0),           # fp128 (IEEE)
    (73, CL_EXTENDED, ST_EXPERIMENTAL,128,1, 7,  0, ENC_POSIT, 42, 0),       # posit128
    (74, CL_EXTENDED, ST_EMPIRICAL,  128, 1, 11,52*2, ENC_FP, 43, 0),        # double-double

    # Cluster 12: Quant-tuned (2)
    (75, CL_QUANT, ST_EXPERIMENTAL, 4, 0, 0, 4, ENC_INT, 44, FLAG_ON_DIE),   # nf4 (bitsandbytes)
    (76, CL_QUANT, ST_EXPERIMENTAL, 4, 0, 0, 4, ENC_INT, 45, 0),             # nf4 ablation

    # Cluster 2 (continued): Blackwell sub-8-bit
    (77, CL_ML_LOW, ST_SPEC,         6, 1, 2, 3, ENC_FP, 12, FLAG_ON_DIE),  # fp6 e2m3 (Blackwell)

    # Cluster 5 (continued): OCP MX scale + integer element types
    (78, CL_OCP_MX, ST_SPEC,  8, 0, 8, 0, ENC_MX, 19, FLAG_ON_DIE),  # E8M0 (shared scale)
    (79, CL_OCP_MX, ST_SPEC,  8, 1, 0, 7, ENC_MX, 19, FLAG_ON_DIE),  # MXINT8
]

assert len(CATALOG) == 80, f"Expected 80 records, got {len(CATALOG)}"


def generate_verilog(records, output_path):
    """Generate format_rom.v from CATALOG records."""
    lines = []
    lines.append("// SPDX-License-Identifier: Apache-2.0")
    lines.append("// tt-trinity-corona / src/rtl/format_rom.v")
    lines.append("// AUTO-GENERATED by tools/gen_rom.py -- DO NOT EDIT BY HAND")
    lines.append(f"// {len(records)} records x 80 bits per specs/corona/rom_layout.t27")
    lines.append("")
    lines.append("`default_nettype none")
    lines.append("")
    lines.append("module format_rom (")
    lines.append("    input  wire        clk,")
    lines.append("    input  wire [6:0]  addr,")
    lines.append("    output reg  [79:0] data")
    lines.append(");")
    lines.append("")
    lines.append("    always @(posedge clk) begin")
    lines.append("        case (addr)")

    for rec in records:
        fmt_id, cluster, status, total, sign, exp, mant, enc, ref, flags = rec
        word = pack_record(fmt_id, cluster, status, total, sign, exp, mant, enc, ref, flags)
        lines.append(f"            7'd{fmt_id:>2}: data <= 80'h{word:020X};")

    lines.append("            default: data <= 80'h0;")
    lines.append("        endcase")
    lines.append("    end")
    lines.append("")
    lines.append("endmodule")
    lines.append("")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Generated {output_path}: {len(records)} records, {len(records)*80} ROM bits")


def generate_python_table(records):
    """Return dict of {fmt_id: packed_80bit_int} for test verification."""
    table = {}
    for rec in records:
        fmt_id = rec[0]
        word = pack_record(*rec)
        table[fmt_id] = word
    return table


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output = os.path.join(script_dir, "..", "src", "rtl", "format_rom.v")
    generate_verilog(CATALOG, output)

    # Verify packing
    table = generate_python_table(CATALOG)
    for fmt_id, word in sorted(table.items()):
        unpacked_id = (word >> 72) & 0xFF
        assert unpacked_id == fmt_id, f"fmt_id mismatch at {fmt_id}: got {unpacked_id}"
    print(f"All {len(table)} records verified: format_index_id round-trips correctly.")
