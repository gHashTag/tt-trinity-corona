// Formal verification: OCP MX FP8 E4M3 → FP32 decode
// bias=7, NaN = S.1111.111 only, has subnormals
`default_nettype none

module fv_mxfp8_e4m3;
    (* anyconst *) wire [7:0] e4m3_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_nan;

    mxfp8_e4m3_decode dut (
        .e4m3_in(e4m3_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_nan(is_nan)
    );

    wire       sign = e4m3_in[7];
    wire [3:0] exp  = e4m3_in[6:3];
    wire [2:0] mant = e4m3_in[2:0];

    // Independent golden reference
    reg [7:0]  g_exp;
    reg [22:0] g_mant;
    always @(*) begin
        if (exp == 4'hF && mant == 3'h7) begin
            g_exp = 8'hFF; g_mant = 23'h400000; // NaN
        end else if (exp == 4'd0 && mant == 3'd0) begin
            g_exp = 8'h00; g_mant = 23'h000000; // Zero
        end else if (exp == 4'd0) begin
            // Subnormal: val = ±2^(-6) × (0.mant)
            if (mant[2]) begin
                g_exp = 8'd120; g_mant = {mant[1:0], 21'b0};
            end else if (mant[1]) begin
                g_exp = 8'd119; g_mant = {mant[0], 22'b0};
            end else begin
                g_exp = 8'd118; g_mant = 23'b0;
            end
        end else begin
            g_exp = {4'b0, exp} + 8'd120;
            g_mant = {mant, 20'b0};
        end
    end

    wire [31:0] golden = {sign, g_exp, g_mant};

    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero == (exp == 4'd0 && mant == 3'd0));
        assert(is_nan  == (exp == 4'hF && mant == 3'h7));
        // OCP E4M3: only ONE NaN encoding (0x7F and 0xFF)
        if (exp == 4'hF && mant != 3'h7)
            assert(fp32_out[30:23] != 8'hFF); // not NaN/Inf
        // Sign always preserved
        assert(fp32_out[31] == sign);

        cover(e4m3_in == 8'h00);  // +0.0
        cover(e4m3_in == 8'h7F);  // +NaN
        cover(e4m3_in == 8'h7E);  // max positive finite
        cover(e4m3_in == 8'h01);  // smallest subnormal
    end
endmodule
