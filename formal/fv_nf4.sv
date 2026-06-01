// Formal verification: NF4 (NormalFloat4, QLoRA) → FP32 LUT decode
`default_nettype none

module fv_nf4;
    (* anyconst *) wire [3:0] nf4_in;
    wire [31:0] fp32_out;

    nf4_decode dut (.nf4_in(nf4_in), .fp32_out(fp32_out));

    // Independent golden LUT (N(0,1) quantiles from bitsandbytes)
    reg [31:0] golden;
    always @(*) begin
        case (nf4_in)
            4'h0: golden = 32'hBF800000;
            4'h1: golden = 32'hBF3239B1;
            4'h2: golden = 32'hBF066B30;
            4'h3: golden = 32'hBECA32A0;
            4'h4: golden = 32'hBE91A24D;
            4'h5: golden = 32'hBE3D353F;
            4'h6: golden = 32'hBDBA7871;
            4'h7: golden = 32'h00000000;
            4'h8: golden = 32'h3DA2FAFF;
            4'h9: golden = 32'h3E24CAE3;
            4'hA: golden = 32'h3E7C04DD;
            4'hB: golden = 32'h3EAD033A;
            4'hC: golden = 32'h3EE1A4B8;
            4'hD: golden = 32'h3F1007AB;
            4'hE: golden = 32'h3F3913B3;
            4'hF: golden = 32'h3F800000;
        endcase
    end

    always @(*) begin
        assert(fp32_out == golden);
        // Boundary: -1.0 at index 0, +1.0 at index 15
        if (nf4_in == 4'h0) assert(fp32_out == 32'hBF800000);
        if (nf4_in == 4'hF) assert(fp32_out == 32'h3F800000);
        // Zero at index 7
        if (nf4_in == 4'h7) assert(fp32_out == 32'h00000000);
        // Monotonic: indices 0-6 are negative (sign=1), 7 is zero, 8-15 positive (sign=0)
        if (nf4_in < 4'h7) assert(fp32_out[31] == 1'b1);
        if (nf4_in == 4'h7) assert(fp32_out == 32'h00000000);
        if (nf4_in > 4'h7) assert(fp32_out[31] == 1'b0);

        cover(nf4_in == 4'h0);  // -1.0 (min)
        cover(nf4_in == 4'h7);  // 0.0 (zero)
        cover(nf4_in == 4'hF);  // +1.0 (max)
        cover(nf4_in == 4'h8);  // smallest positive
    end
endmodule
