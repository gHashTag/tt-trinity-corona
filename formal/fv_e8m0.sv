// Formal verification: E8M0 exponent-only decode
`default_nettype none

module fv_e8m0;
    (* anyconst *) wire [7:0] e8m0_in;
    wire [31:0] fp32_out;
    wire        is_nan;

    e8m0_decode dut (.e8m0_in(e8m0_in), .fp32_out(fp32_out), .is_nan(is_nan));

    // Golden: independent computation
    reg [31:0] golden;
    always @(*) begin
        if (e8m0_in == 8'hFF)
            golden = 32'h7FC00000;
        else if (e8m0_in == 8'h00)
            golden = 32'h00400000;
        else
            golden = {1'b0, e8m0_in, 23'b0};
    end

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_nan == (e8m0_in == 8'hFF));
        // E8M0 is unsigned — sign bit always 0 (except NaN)
        if (e8m0_in != 8'hFF) assert(fp32_out[31] == 1'b0);
        // Non-NaN, non-zero: mantissa is always zero (pure power of 2)
        if (e8m0_in != 8'hFF && e8m0_in != 8'h00)
            assert(fp32_out[22:0] == 23'b0);
    end
endmodule
