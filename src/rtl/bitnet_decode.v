// SPDX-License-Identifier: Apache-2.0
// tt-trinity-corona / src/rtl/bitnet_decode.v
// BitNet 1.58b ternary {-1, 0, +1} -> FP32 decode.
// 2-bit input: 00=0, 01=+1, 10=-1, 11=reserved(NaN).

`default_nettype none

module bitnet_decode (
    input  wire [1:0]  ternary_in,
    output reg  [31:0] fp32_out,
    output wire        is_zero,
    output wire        is_reserved
);

    assign is_zero     = (ternary_in == 2'b00);
    assign is_reserved = (ternary_in == 2'b11);

    always @(*) begin
        case (ternary_in)
            2'b00:   fp32_out = 32'h00000000; // 0
            2'b01:   fp32_out = 32'h3F800000; // +1.0
            2'b10:   fp32_out = 32'hBF800000; // -1.0
            2'b11:   fp32_out = 32'h7FC00000; // NaN (reserved)
            default: fp32_out = 32'h7FC00000;
        endcase
    end

endmodule
