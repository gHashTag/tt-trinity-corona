// Formal verification: FP6 E3M2 → FP32 decode
// Verifies subnormal normalization for 2-bit mantissa
`default_nettype none

module fv_fp6_e3m2;
    (* anyconst *) wire [5:0] fp6_in;
    wire [31:0] fp32_out;

    fp6_e3m2_decode dut (.fp6_in(fp6_in), .fp32_out(fp32_out));

    wire       sign = fp6_in[5];
    wire [2:0] exp  = fp6_in[4:2];
    wire [1:0] mant = fp6_in[1:0];

    // Independent golden reference
    reg [7:0]  g_exp;
    reg [22:0] g_mant;
    always @(*) begin
        if (exp == 3'd0 && mant == 2'd0) begin
            g_exp = 8'd0; g_mant = 23'd0;
        end else if (exp == 3'd0) begin
            if (mant[1]) begin
                g_exp = 8'd124; g_mant = {mant[0], 22'b0};
            end else begin
                g_exp = 8'd123; g_mant = 23'b0;
            end
        end else begin
            g_exp = {5'b0, exp} + 8'd124;
            g_mant = {mant, 21'b0};
        end
    end

    wire [31:0] golden = {sign, g_exp, g_mant};

    always @(*) begin
        assert(fp32_out == golden);
        // Sign always preserved
        assert(fp32_out[31] == sign);
        // No NaN or Inf in FP6 E3M2
        if (exp != 3'd0 || mant != 2'd0)
            assert(fp32_out[30:23] != 8'hFF);

        cover(fp6_in == 6'h00);  // +0.0
        cover(fp6_in == 6'h1F);  // max positive
        cover(fp6_in == 6'h20);  // -0.0
        cover(fp6_in == 6'h01);  // smallest subnormal
    end
endmodule
