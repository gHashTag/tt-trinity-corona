// SPDX-License-Identifier: Apache-2.0
// Formal verification: BF16 → FP32 decode (structural wiring proof)
`default_nettype none

module fv_bf16;
    (* anyconst *) wire [15:0] bf16_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_inf, is_nan;

    bf16_decode dut (
        .bf16_in(bf16_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_inf(is_inf), .is_nan(is_nan)
    );

    wire [7:0] exp  = bf16_in[14:7];
    wire [6:0] mant = bf16_in[6:0];

    always @(*) begin
        // Core: BF16 is upper 16 bits of FP32
        assert(fp32_out == {bf16_in, 16'b0});
        // Classification flags
        assert(is_zero == (exp == 8'h00 && mant == 7'h00));
        assert(is_inf  == (exp == 8'hFF && mant == 7'h00));
        assert(is_nan  == (exp == 8'hFF && mant != 7'h00));
        // Mutual exclusion
        assert(!(is_zero && is_inf));
        assert(!(is_zero && is_nan));
        assert(!(is_inf && is_nan));

        cover(bf16_in == 16'h0000);  // +0.0
        cover(bf16_in == 16'h3F80);  // +1.0
        cover(bf16_in == 16'h7F80);  // +Inf
        cover(bf16_in == 16'h7FC0);  // NaN
    end
endmodule
