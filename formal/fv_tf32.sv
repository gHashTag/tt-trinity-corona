// SPDX-License-Identifier: Apache-2.0
// Formal verification: TF32 → FP32 decode (structural wiring proof)
`default_nettype none

module fv_tf32;
    (* anyconst *) wire [18:0] tf32_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_inf, is_nan;

    tf32_decode dut (
        .tf32_in(tf32_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_inf(is_inf), .is_nan(is_nan)
    );

    wire       sign = tf32_in[18];
    wire [7:0] exp  = tf32_in[17:10];
    wire [9:0] mant = tf32_in[9:0];

    always @(*) begin
        // Core: TF32 is FP32 with truncated mantissa (10 of 23 bits)
        assert(fp32_out == {sign, exp, mant, 13'b0});
        // Classification
        assert(is_zero == (exp == 8'd0 && mant == 10'd0));
        assert(is_inf  == (exp == 8'hFF && mant == 10'd0));
        assert(is_nan  == (exp == 8'hFF && mant != 10'd0));
        // Mutual exclusion
        assert(!(is_zero && is_inf));
        assert(!(is_zero && is_nan));
        assert(!(is_inf && is_nan));
        // Sign always preserved
        assert(fp32_out[31] == sign);
        // Lower 13 mantissa bits always zero
        assert(fp32_out[12:0] == 13'b0);

        cover(tf32_in == 19'h00000);  // +0.0
        cover(tf32_in == 19'h1FC00);  // +1.0
        cover(tf32_in == 19'h3FC00);  // +Inf
        cover(tf32_in == 19'h3FC01);  // NaN
    end
endmodule
