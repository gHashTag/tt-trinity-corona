// SPDX-License-Identifier: Apache-2.0
// tt-trinity-corona / src/rtl/mxfp8_e4m3_decode.v
// OCP MX FP8 E4M3 -> FP32 decode.
// E4M3: 1 sign + 4 exp (bias=7) + 3 mantissa. No infinity. NaN = S.1111.111 only.

`default_nettype none

module mxfp8_e4m3_decode (
    input  wire [7:0]  e4m3_in,
    output reg  [31:0] fp32_out,
    output wire        is_zero,
    output wire        is_nan
);

    wire        sign = e4m3_in[7];
    wire [3:0]  exp  = e4m3_in[6:3];
    wire [2:0]  mant = e4m3_in[2:0];

    assign is_zero = (exp == 4'd0) && (mant == 3'd0);
    assign is_nan  = (exp == 4'hF) && (mant == 3'h7);

    // Subnormal normalization: find leading 1 position in 3-bit mantissa
    // mant=001 -> shift=2, normalized_mant=000, adj_exp=1
    // mant=01x -> shift=1, normalized_mant=x00, adj_exp=2
    // mant=1xx -> shift=0, normalized_mant=xx0, adj_exp=3
    reg [7:0]  fp32_exp;
    reg [22:0] fp32_mant;

    always @(*) begin
        if (is_nan) begin
            fp32_exp  = 8'hFF;
            fp32_mant = 23'h400000;   // quiet NaN
        end else if (is_zero) begin
            fp32_exp  = 8'h00;
            fp32_mant = 23'h000000;
        end else if (exp == 4'd0) begin
            // Subnormal: value = (-1)^S * 2^(-6) * (0.mant)
            // Normalize by shifting mantissa left until leading 1 found
            if (mant[2]) begin
                fp32_exp  = 8'd121;           // -7+1+127 = 121
                fp32_mant = {mant[1:0], 21'b0};
            end else if (mant[1]) begin
                fp32_exp  = 8'd120;           // -7+0+127 = 120
                fp32_mant = {mant[0], 22'b0};
            end else begin
                fp32_exp  = 8'd119;           // -7-1+127 = 119
                fp32_mant = 23'b0;
            end
        end else begin
            // Normal: value = (-1)^S * 2^(exp-7) * (1.mant)
            // FP32 exp = exp - 7 + 127 = exp + 120
            fp32_exp  = {4'b0, exp} + 8'd120;
            fp32_mant = {mant, 20'b0};
        end
    end

    always @(*) begin
        fp32_out = {sign, fp32_exp, fp32_mant};
    end

endmodule
