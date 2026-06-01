// SPDX-License-Identifier: Apache-2.0
// Formal verification: MXINT8 -> FP32 decode
// Exhaustive golden reference: algorithmic int8-to-FP32 with 2^(-6) scale.
// Covers all 256 input values via independent leading-one computation.
`default_nettype none

module fv_mxint8;
    (* anyconst *) wire [7:0] mxint8_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_reserved;

    mxint8_decode dut (
        .mxint8_in(mxint8_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_reserved(is_reserved)
    );

    // ── Independent golden reference ───────────────────────────────
    // MXINT8: 8-bit two's complement, value = int8 * 2^(-6).
    // -128 (0x80) is reserved -> qNaN.  0 -> +0.0.
    // For |val| in [1,127]: FP32 = (-1)^sign * 2^(lop-6) * (1.frac)
    //   where lop = leading-one position of |val| (0..6),
    //   FP32 exponent = 127 + lop - 6 = 121 + lop,
    //   FP32 mantissa = remaining bits below leading one, left-aligned to 23b.

    wire g_sign = mxint8_in[7];

    // Two's complement magnitude (7-bit). For 0x80, abs_val is don't-care
    // because the reserved case is handled separately.
    wire [6:0] g_abs = g_sign ? (~mxint8_in[6:0] + 7'd1) : mxint8_in[6:0];

    // Leading-one position in g_abs[6:0]
    reg [2:0] g_lop;
    always @(*) begin
        casez (g_abs)
            7'b1??????: g_lop = 3'd6;
            7'b01?????: g_lop = 3'd5;
            7'b001????: g_lop = 3'd4;
            7'b0001???: g_lop = 3'd3;
            7'b00001??: g_lop = 3'd2;
            7'b000001?: g_lop = 3'd1;
            7'b0000001: g_lop = 3'd0;
            default:    g_lop = 3'd0; // abs=0, but handled by is_zero path
        endcase
    end

    // FP32 exponent = 127 + (lop - 6) = 121 + lop
    wire [7:0] g_exp = 8'd121 + {5'b0, g_lop};

    // FP32 mantissa: strip the implicit leading 1, left-align to 23 bits.
    // For lop=k, the leading 1 is at bit k of g_abs.  The remaining k bits
    // below it are shifted left by (23 - k) to fill the 23-bit mantissa.
    reg [22:0] g_mant;
    always @(*) begin
        case (g_lop)
            3'd6: g_mant = {g_abs[5:0], 17'b0};
            3'd5: g_mant = {g_abs[4:0], 18'b0};
            3'd4: g_mant = {g_abs[3:0], 19'b0};
            3'd3: g_mant = {g_abs[2:0], 20'b0};
            3'd2: g_mant = {g_abs[1:0], 21'b0};
            3'd1: g_mant = {g_abs[0],   22'b0};
            3'd0: g_mant = 23'b0;
            default: g_mant = 23'b0;
        endcase
    end

    // Assemble golden FP32
    reg [31:0] golden;
    always @(*) begin
        if (mxint8_in == 8'h00)
            golden = 32'h00000000;          // +0.0
        else if (mxint8_in == 8'h80)
            golden = 32'h7FC00000;          // qNaN (reserved -128)
        else
            golden = {g_sign, g_exp, g_mant};
    end

    // ── Assertions ─────────────────────────────────────────────────
    // Primary: DUT output must match golden for ALL 256 input values.
    always @(*) begin
        assert(fp32_out == golden);
    end

    // Flag consistency
    always @(*) begin
        assert(is_zero     == (mxint8_in == 8'h00));
        assert(is_reserved == (mxint8_in == 8'h80));
    end

    // Sign preservation for non-special values
    always @(*) begin
        if (mxint8_in != 8'h00 && mxint8_in != 8'h80)
            assert(fp32_out[31] == mxint8_in[7]);
    end

    // FP32 exponent range for normal values: 121 (lop=0, |val|=1) to 127 (lop=6, |val|>=64)
    always @(*) begin
        if (mxint8_in != 8'h00 && mxint8_in != 8'h80)
            assert(fp32_out[30:23] >= 8'd121 && fp32_out[30:23] <= 8'd127);
    end

    // Positive non-zero values produce strictly positive FP32
    always @(*) begin
        if (mxint8_in[7] == 1'b0 && mxint8_in != 8'h00)
            assert(fp32_out[31] == 1'b0 && fp32_out != 32'h00000000);
    end

    // ── Spot-check assertions (documentation & regression) ─────────
    //  hex  | int8  | value     | FP32
    // ------+-------+-----------+------------
    //  0x00 |    0  |  0.0      | 0x00000000
    //  0x01 |   +1  | +1/64     | 0x3C800000
    //  0x02 |   +2  | +2/64     | 0x3D000000
    //  0x03 |   +3  | +3/64     | 0x3D400000
    //  0x04 |   +4  | +4/64     | 0x3D800000
    //  0x20 |  +32  | +32/64    | 0x3F000000
    //  0x3F |  +63  | +63/64    | 0x3F7C0000
    //  0x40 |  +64  | +1.0      | 0x3F800000
    //  0x41 |  +65  | +65/64    | 0x3F820000
    //  0x7F | +127  | +127/64   | 0x3FFE0000
    //  0x80 | -128  | reserved  | 0x7FC00000 (NaN)
    //  0x81 | -127  | -127/64   | 0xBFFE0000
    //  0xC0 |  -64  | -1.0      | 0xBF800000
    //  0xFE |   -2  | -2/64     | 0xBD000000
    //  0xFF |   -1  | -1/64     | 0xBC800000
    always @(*) begin
        if (mxint8_in == 8'h00) assert(fp32_out == 32'h00000000);
        if (mxint8_in == 8'h01) assert(fp32_out == 32'h3C800000);
        if (mxint8_in == 8'h02) assert(fp32_out == 32'h3D000000);
        if (mxint8_in == 8'h03) assert(fp32_out == 32'h3D400000);
        if (mxint8_in == 8'h04) assert(fp32_out == 32'h3D800000);
        if (mxint8_in == 8'h20) assert(fp32_out == 32'h3F000000);
        if (mxint8_in == 8'h3F) assert(fp32_out == 32'h3F7C0000);
        if (mxint8_in == 8'h40) assert(fp32_out == 32'h3F800000);
        if (mxint8_in == 8'h41) assert(fp32_out == 32'h3F820000);
        if (mxint8_in == 8'h7F) assert(fp32_out == 32'h3FFE0000);
        if (mxint8_in == 8'h80) assert(fp32_out == 32'h7FC00000);
        if (mxint8_in == 8'h81) assert(fp32_out == 32'hBFFE0000);
        if (mxint8_in == 8'hC0) assert(fp32_out == 32'hBF800000);
        if (mxint8_in == 8'hFE) assert(fp32_out == 32'hBD000000);
        if (mxint8_in == 8'hFF) assert(fp32_out == 32'hBC800000);

        cover(mxint8_in == 8'h00);  // zero
        cover(mxint8_in == 8'h40);  // +1.0 (64/64)
        cover(mxint8_in == 8'h7F);  // max positive (+127/64)
        cover(mxint8_in == 8'h80);  // reserved (NaN)
    end

endmodule
