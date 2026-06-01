// SPDX-License-Identifier: Apache-2.0
// Formal verification: FP6 E2M3 → FP32 decode
// Blackwell tensor core format: 1s + 2e(bias=1) + 3m, no Inf/NaN
`default_nettype none

module fv_fp6_e2m3;
    (* anyconst *) wire [5:0] fp6_in;
    wire [31:0] fp32_out;
    wire        is_zero;

    fp6_e2m3_decode dut (.fp6_in(fp6_in), .fp32_out(fp32_out), .is_zero(is_zero));

    wire       sign = fp6_in[5];
    wire [1:0] exp  = fp6_in[4:3];
    wire [2:0] mant = fp6_in[2:0];

    // Independent golden reference
    reg [7:0]  g_exp;
    reg [22:0] g_mant;
    always @(*) begin
        if (exp == 2'd0 && mant == 3'd0) begin
            g_exp = 8'd0; g_mant = 23'd0;
        end else if (exp == 2'd0) begin
            if (mant[2]) begin
                g_exp = 8'd126; g_mant = {mant[1:0], 21'b0};
            end else if (mant[1]) begin
                g_exp = 8'd125; g_mant = {mant[0], 22'b0};
            end else begin
                g_exp = 8'd124; g_mant = 23'b0;
            end
        end else begin
            g_exp = {6'b0, exp} + 8'd126;
            g_mant = {mant, 20'b0};
        end
    end

    wire [31:0] golden = {sign, g_exp, g_mant};

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero == (exp == 2'd0 && mant == 3'd0));
        assert(fp32_out[31] == sign);
        // No NaN or Inf in E2M3
        assert(fp32_out[30:23] != 8'hFF);
        // Normal range: exp 1-3 maps to FP32 exp 127-129
        if (exp > 2'd0) assert(fp32_out[30:23] >= 8'd127);

        cover(fp6_in == 6'h00);  // +0.0
        cover(fp6_in == 6'h1F);  // max positive
        cover(fp6_in == 6'h20);  // -0.0
        cover(fp6_in == 6'h01);  // smallest subnormal
    end
endmodule
