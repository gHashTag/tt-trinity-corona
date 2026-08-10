// SPDX-License-Identifier: Apache-2.0
// tt-trinity-corona / src/rtl/fp6_e3m2_decode.v
// FP6 E3M2 -> FP32 decode per OCP MX spec.
// Format: 1 sign + 3 exp (bias=3) + 2 mantissa. No NaN, no Inf.

`default_nettype none

module fp6_e3m2_decode (
    input  wire [5:0]  fp6_in,
    output reg  [31:0] fp32_out
);

    wire       sign = fp6_in[5];
    wire [2:0] exp  = fp6_in[4:2];
    wire [1:0] mant = fp6_in[1:0];

    wire is_zero      = (exp == 3'd0) && (mant == 2'd0);
    wire is_subnormal = (exp == 3'd0) && (mant != 2'd0);
    // No is_saturate here. FP6 E3M2 reserves NO encodings: exponent 7 is an
    // ordinary exponent (E = 7-3 = 4) and the top group holds four ordinary
    // values, so the format maximum is 1.75 * 2^4 = 28.0. This used to clamp
    // the whole group to 14.0, which lost 8 of the 64 code points including
    // the maximum. OCP MX does say conversion saturates rather than producing
    // Inf -- but that is a rule about the ENCODER. Decoding a code point that
    // carries the top exponent is just reading a number. The convention that
    // was borrowed belongs to FP8 E4M3/E5M2, which do reserve their top
    // exponent; FP6 does not.

    reg [7:0]  fp32_exp;
    reg [22:0] fp32_mant;

    always @(*) begin
        if (is_zero) begin
            fp32_exp  = 8'd0;
            fp32_mant = 23'd0;
        end else if (is_subnormal) begin
            // Subnormal: value = (-1)^S * 2^(-2) * (0.mant)
            // Normalize: find leading 1 in 2-bit mantissa
            if (mant[1]) begin
                // mant = 1x: shift by 0, normalized = x0...0
                fp32_exp  = 8'd124;  // -3+0+127 = 124
                fp32_mant = {mant[0], 22'b0};
            end else begin
                // mant = 01: shift by 1
                fp32_exp  = 8'd123;  // -3-1+127 = 123
                fp32_mant = 23'b0;
            end
        end else begin
            // Normal, including exp == 7: FP32 exp = exp - 3 + 127 = exp + 124
            fp32_exp  = {5'b0, exp} + 8'd124;
            fp32_mant = {mant, 21'b0};
        end
    end

    always @(*) begin
        fp32_out = {sign, fp32_exp, fp32_mant};
    end

endmodule
