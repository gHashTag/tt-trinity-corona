// Formal verification: FP8 E5M2 → FP32 decode
// Independently verifies subnormal normalization, Inf/NaN classification
`default_nettype none

module fv_fp8_e5m2;
    (* anyconst *) wire [7:0] e5m2_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_inf, is_nan;

    fp8_e5m2_decode dut (
        .e5m2_in(e5m2_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_inf(is_inf), .is_nan(is_nan)
    );

    wire       sign = e5m2_in[7];
    wire [4:0] exp  = e5m2_in[6:2];
    wire [1:0] mant = e5m2_in[1:0];

    // Independent golden reference
    reg [7:0]  g_exp;
    reg [22:0] g_mant;
    always @(*) begin
        if (exp == 5'h1F && mant == 2'd0) begin
            g_exp = 8'hFF; g_mant = 23'h000000; // Inf
        end else if (exp == 5'h1F && mant != 2'd0) begin
            g_exp = 8'hFF; g_mant = 23'h400000; // qNaN
        end else if (exp == 5'd0 && mant == 2'd0) begin
            g_exp = 8'h00; g_mant = 23'h000000; // Zero
        end else if (exp == 5'd0) begin
            // Subnormal: val = ±2^(-14) × (0.mant)
            if (mant[1]) begin
                g_exp = 8'd112; g_mant = {mant[0], 22'b0};
            end else begin
                g_exp = 8'd111; g_mant = 23'b0;
            end
        end else begin
            g_exp = {3'b0, exp} + 8'd112;
            g_mant = {mant, 21'b0};
        end
    end

    wire [31:0] golden = {sign, g_exp, g_mant};

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero == (exp == 5'd0 && mant == 2'd0));
        assert(is_inf  == (exp == 5'h1F && mant == 2'd0));
        assert(is_nan  == (exp == 5'h1F && mant != 2'd0));
        // Sign preservation
        assert(fp32_out[31] == sign);
        // Normal range: FP32 exponent must be in [113, 142]
        if (exp > 5'd0 && exp < 5'h1F)
            assert(fp32_out[30:23] >= 8'd113 && fp32_out[30:23] <= 8'd142);

        cover(e5m2_in == 8'h00);  // +0.0
        cover(e5m2_in == 8'h7C);  // +Inf
        cover(e5m2_in == 8'h7F);  // NaN
        cover(e5m2_in == 8'h01);  // smallest subnormal
    end
endmodule
