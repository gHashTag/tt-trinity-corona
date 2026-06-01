// Formal verification: Posit8(es=0) → FP32 decode
// Most complex decoder — verifies regime extraction, fraction alignment
`default_nettype none

module fv_posit8;
    (* anyconst *) wire [7:0] posit_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_nar;

    posit8_decode dut (
        .posit_in(posit_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_nar(is_nar)
    );

    always @(*) begin
        assert(is_zero == (posit_in == 8'h00));
        assert(is_nar  == (posit_in == 8'h80));

        // Special values
        if (posit_in == 8'h00) assert(fp32_out == 32'h00000000);
        if (posit_in == 8'h80) assert(fp32_out == 32'h7FC00000);

        // Known posit8 values (from posit standard)
        // +1 = 0x40: regime=01 (k=0), no fraction → 2^0 = 1.0
        if (posit_in == 8'h40) assert(fp32_out == 32'h3F800000);
        // -1 = 0xC0: sign=1, abs=0x40 → -1.0
        if (posit_in == 8'hC0) assert(fp32_out == 32'hBF800000);
        // +2 = 0x60: regime=10 (k=1), no fraction → 2^1 = 2.0
        if (posit_in == 8'h60) assert(fp32_out == 32'h40000000);
        // +0.5 = 0x20: regime=001 (k=-1), no fraction → 2^(-1) = 0.5
        if (posit_in == 8'h20) assert(fp32_out == 32'h3F000000);
        // +4 = 0x70: regime=110 (k=2) → 2^2 = 4.0
        if (posit_in == 8'h70) assert(fp32_out == 32'h40800000);
        // +0.25 = 0x10: regime=0001 (k=-2) → 2^(-2) = 0.25
        if (posit_in == 8'h10) assert(fp32_out == 32'h3E800000);
        // maxpos = 0x7F: regime=1111111 (k=6) → 2^6 = 64.0
        if (posit_in == 8'h7F) assert(fp32_out == 32'h42800000);
        // minpos = 0x01: regime=0000001 (k=-6) → 2^(-6) = 1/64
        if (posit_in == 8'h01) assert(fp32_out == 32'h3C800000);

        // +1.25 = 0x48: regime=10 (k=0), frac=01000 → 2^0 × 1.25
        if (posit_in == 8'h48) assert(fp32_out == 32'h3FA00000);
        // +1.5 = 0x50: regime=10 (k=0), frac=10000 → 2^0 × 1.5
        if (posit_in == 8'h50) assert(fp32_out == 32'h3FC00000);
        // +3.0 = 0x68: regime=110 (k=1), frac=1000 → 2^1 × 1.5
        if (posit_in == 8'h68) assert(fp32_out == 32'h40400000);

        // Sign: negative posit → negative FP32 (except zero/NaR)
        if (posit_in[7] && posit_in != 8'h80)
            assert(fp32_out[31] == 1'b1);
        if (!posit_in[7] && posit_in != 8'h00)
            assert(fp32_out[31] == 1'b0);
    end
endmodule
