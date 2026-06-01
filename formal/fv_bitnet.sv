// SPDX-License-Identifier: Apache-2.0
// Formal verification: BitNet 1.58b ternary → FP32 decode
`default_nettype none

module fv_bitnet;
    (* anyconst *) wire [1:0] ternary_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_reserved;

    bitnet_decode dut (
        .ternary_in(ternary_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_reserved(is_reserved)
    );

    // Independent golden: 00=0, 01=+1.0, 10=-1.0, 11=NaN
    reg [31:0] golden;
    always @(*) begin
        case (ternary_in)
            2'b00: golden = 32'h00000000;
            2'b01: golden = 32'h3F800000;
            2'b10: golden = 32'hBF800000;
            2'b11: golden = 32'h7FC00000;
        endcase
    end

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero     == (ternary_in == 2'b00));
        assert(is_reserved == (ternary_in == 2'b11));
        // Only three valid numeric values: 0, +1, -1
        if (ternary_in != 2'b11)
            assert(fp32_out == 32'h00000000 ||
                   fp32_out == 32'h3F800000 ||
                   fp32_out == 32'hBF800000);
        // Reserved → quiet NaN
        if (ternary_in == 2'b11)
            assert(fp32_out == 32'h7FC00000);

        cover(ternary_in == 2'b00);  // zero
        cover(ternary_in == 2'b01);  // +1
        cover(ternary_in == 2'b10);  // -1
        cover(ternary_in == 2'b11);  // NaN (reserved)
    end
endmodule
