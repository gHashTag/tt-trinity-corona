// SPDX-License-Identifier: Apache-2.0
// Formal verification: FP4 E2M1 → FP32 LUT decode
// Verifies structural properties: sign preservation, symmetry, ordering
`default_nettype none

module fv_fp4;
    (* anyconst *) wire [3:0] fp4_in;
    wire [31:0] fp32_out;

    fp4_decode dut (.fp4_in(fp4_in), .fp32_out(fp32_out));

    // Independent golden LUT
    reg [31:0] golden;
    always @(*) begin
        case (fp4_in)
            4'h0: golden = 32'h00000000;
            4'h1: golden = 32'h3F000000;
            4'h2: golden = 32'h3F800000;
            4'h3: golden = 32'h3FC00000;
            4'h4: golden = 32'h40000000;
            4'h5: golden = 32'h40400000;
            4'h6: golden = 32'h40800000;
            4'h7: golden = 32'h40C00000;
            4'h8: golden = 32'h80000000;
            4'h9: golden = 32'hBF000000;
            4'hA: golden = 32'hBF800000;
            4'hB: golden = 32'hBFC00000;
            4'hC: golden = 32'hC0000000;
            4'hD: golden = 32'hC0400000;
            4'hE: golden = 32'hC0800000;
            4'hF: golden = 32'hC0C00000;
        endcase
    end

    always @(*) begin
        assert(fp32_out == golden);
        // Sign bit = fp4 MSB
        assert(fp32_out[31] == fp4_in[3]);
        // Symmetry: |fp4(x)| == |fp4(x ^ 8)| (positive/negative mirror)
        // Zero encodings
        if (fp4_in == 4'h0) assert(fp32_out == 32'h00000000);
        if (fp4_in == 4'h8) assert(fp32_out == 32'h80000000);
        // ±1.0 at positions 2 and A
        if (fp4_in == 4'h2) assert(fp32_out == 32'h3F800000);
        if (fp4_in == 4'hA) assert(fp32_out == 32'hBF800000);

        cover(fp4_in == 4'h0);  // +0.0
        cover(fp4_in == 4'h7);  // +6.0 (max positive)
        cover(fp4_in == 4'hF);  // -6.0 (max negative)
        cover(fp4_in == 4'h2);  // +1.0
    end
endmodule
