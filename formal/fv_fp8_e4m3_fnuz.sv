// SPDX-License-Identifier: Apache-2.0
// Formal verification: FP8 E4M3 FNUZ → FP32 decode
// AMD MI300 variant: bias=8, 0x80=NaN, no -0, has subnormals
`default_nettype none

module fv_fp8_e4m3_fnuz;
    (* anyconst *) wire [7:0] e4m3_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_nan;

    fp8_e4m3_fnuz_decode dut (
        .e4m3_in(e4m3_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_nan(is_nan)
    );

    wire       sign = e4m3_in[7];
    wire [3:0] exp  = e4m3_in[6:3];
    wire [2:0] mant = e4m3_in[2:0];

    // Independent golden reference
    reg [31:0] golden;
    always @(*) begin
        if (e4m3_in == 8'h80) begin
            golden = 32'h7FC00000; // NaN (positive qNaN, sign NOT preserved)
        end else if (e4m3_in == 8'h00) begin
            golden = 32'h00000000;
        end else if (exp == 4'd0) begin
            // Subnormal: val = ±2^(1-8) × (M/8) = ±M × 2^(-10)
            if (mant[2])
                golden = {sign, 8'd119, mant[1:0], 21'b0};
            else if (mant[1])
                golden = {sign, 8'd118, mant[0], 22'b0};
            else
                golden = {sign, 8'd117, 23'b0};
        end else begin
            // Normal: val = ±2^(E-8) × (1 + M/8)
            golden = {sign, {4'b0, exp} + 8'd119, mant, 20'b0};
        end
    end

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero == (e4m3_in == 8'h00));
        assert(is_nan  == (e4m3_in == 8'h80));
        // Critical FNUZ property: NaN is always POSITIVE qNaN
        if (e4m3_in == 8'h80) assert(fp32_out == 32'h7FC00000);
        // No negative zero in FNUZ
        assert(fp32_out != 32'h80000000 || e4m3_in == 8'h00);

        cover(e4m3_in == 8'h00);  // zero
        cover(e4m3_in == 8'h80);  // NaN
        cover(e4m3_in == 8'h7F);  // max positive
        cover(e4m3_in == 8'h01);  // smallest subnormal
    end
endmodule
