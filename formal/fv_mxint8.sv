// Formal verification: MXINT8 → FP32 decode
// Verifies leading-one detection and normalization independently
`default_nettype none

module fv_mxint8;
    (* anyconst *) wire [7:0] mxint8_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_reserved;

    mxint8_decode dut (
        .mxint8_in(mxint8_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_reserved(is_reserved)
    );

    always @(*) begin
        assert(is_zero     == (mxint8_in == 8'h00));
        assert(is_reserved == (mxint8_in == 8'h80));

        // Zero → FP32 zero
        if (mxint8_in == 8'h00)
            assert(fp32_out == 32'h00000000);

        // Reserved -128 → NaN
        if (mxint8_in == 8'h80)
            assert(fp32_out == 32'h7FC00000);

        // Sign preservation for non-special values
        if (mxint8_in != 8'h00 && mxint8_in != 8'h80)
            assert(fp32_out[31] == mxint8_in[7]);

        // Known values: +1 (0x01) → 1/64 = 2^(-6) = 0x3C800000
        if (mxint8_in == 8'h01)
            assert(fp32_out == 32'h3C800000);

        // +64 (0x40) → 64/64 = 1.0 = 0x3F800000
        if (mxint8_in == 8'h40)
            assert(fp32_out == 32'h3F800000);

        // +127 (0x7F) → 127/64 = 1.984375 = 0x3FFE0000
        if (mxint8_in == 8'h7F)
            assert(fp32_out == 32'h3FFE0000);

        // -1 (0xFF) → -1/64 = 0xBC800000
        if (mxint8_in == 8'hFF)
            assert(fp32_out == 32'hBC800000);

        // All positive non-zero values → positive FP32 output
        if (mxint8_in[7] == 1'b0 && mxint8_in != 8'h00)
            assert(fp32_out[31] == 1'b0 && fp32_out != 32'h00000000);
    end
endmodule
