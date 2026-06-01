// Formal verification: Posit8(es=0) → FP32 decode
// Exhaustive 256-entry golden LUT cross-validated against johndcook.com/eightbit.html
`default_nettype none

module fv_posit8;
    (* anyconst *) wire [7:0] posit_in;
    wire [31:0] fp32_out;
    wire        is_zero, is_nar;

    posit8_decode dut (
        .posit_in(posit_in), .fp32_out(fp32_out),
        .is_zero(is_zero), .is_nar(is_nar)
    );

    // Exhaustive golden reference: all 256 Posit(8,0) → FP32 values
    reg [31:0] golden;
    always @(*) begin
        case (posit_in)
            8'h00: golden = 32'h00000000; // zero
            8'h01: golden = 32'h3C800000; // 1/64
            8'h02: golden = 32'h3D000000; // 1/32
            8'h03: golden = 32'h3D400000; // 3/64
            8'h04: golden = 32'h3D800000; // 1/16
            8'h05: golden = 32'h3DA00000; // 5/64
            8'h06: golden = 32'h3DC00000; // 3/32
            8'h07: golden = 32'h3DE00000; // 7/64
            8'h08: golden = 32'h3E000000; // 1/8
            8'h09: golden = 32'h3E100000; // 9/64
            8'h0A: golden = 32'h3E200000; // 5/32
            8'h0B: golden = 32'h3E300000; // 11/64
            8'h0C: golden = 32'h3E400000; // 3/16
            8'h0D: golden = 32'h3E500000; // 13/64
            8'h0E: golden = 32'h3E600000; // 7/32
            8'h0F: golden = 32'h3E700000; // 15/64
            8'h10: golden = 32'h3E800000; // 1/4
            8'h11: golden = 32'h3E880000; // 17/64
            8'h12: golden = 32'h3E900000; // 9/32
            8'h13: golden = 32'h3E980000; // 19/64
            8'h14: golden = 32'h3EA00000; // 5/16
            8'h15: golden = 32'h3EA80000; // 21/64
            8'h16: golden = 32'h3EB00000; // 11/32
            8'h17: golden = 32'h3EB80000; // 23/64
            8'h18: golden = 32'h3EC00000; // 3/8
            8'h19: golden = 32'h3EC80000; // 25/64
            8'h1A: golden = 32'h3ED00000; // 13/32
            8'h1B: golden = 32'h3ED80000; // 27/64
            8'h1C: golden = 32'h3EE00000; // 7/16
            8'h1D: golden = 32'h3EE80000; // 29/64
            8'h1E: golden = 32'h3EF00000; // 15/32
            8'h1F: golden = 32'h3EF80000; // 31/64
            8'h20: golden = 32'h3F000000; // 1/2
            8'h21: golden = 32'h3F040000; // 33/64
            8'h22: golden = 32'h3F080000; // 17/32
            8'h23: golden = 32'h3F0C0000; // 35/64
            8'h24: golden = 32'h3F100000; // 9/16
            8'h25: golden = 32'h3F140000; // 37/64
            8'h26: golden = 32'h3F180000; // 19/32
            8'h27: golden = 32'h3F1C0000; // 39/64
            8'h28: golden = 32'h3F200000; // 5/8
            8'h29: golden = 32'h3F240000; // 41/64
            8'h2A: golden = 32'h3F280000; // 21/32
            8'h2B: golden = 32'h3F2C0000; // 43/64
            8'h2C: golden = 32'h3F300000; // 11/16
            8'h2D: golden = 32'h3F340000; // 45/64
            8'h2E: golden = 32'h3F380000; // 23/32
            8'h2F: golden = 32'h3F3C0000; // 47/64
            8'h30: golden = 32'h3F400000; // 3/4
            8'h31: golden = 32'h3F440000; // 49/64
            8'h32: golden = 32'h3F480000; // 25/32
            8'h33: golden = 32'h3F4C0000; // 51/64
            8'h34: golden = 32'h3F500000; // 13/16
            8'h35: golden = 32'h3F540000; // 53/64
            8'h36: golden = 32'h3F580000; // 27/32
            8'h37: golden = 32'h3F5C0000; // 55/64
            8'h38: golden = 32'h3F600000; // 7/8
            8'h39: golden = 32'h3F640000; // 57/64
            8'h3A: golden = 32'h3F680000; // 29/32
            8'h3B: golden = 32'h3F6C0000; // 59/64
            8'h3C: golden = 32'h3F700000; // 15/16
            8'h3D: golden = 32'h3F740000; // 61/64
            8'h3E: golden = 32'h3F780000; // 31/32
            8'h3F: golden = 32'h3F7C0000; // 63/64
            8'h40: golden = 32'h3F800000; // 1
            8'h41: golden = 32'h3F840000; // 33/32
            8'h42: golden = 32'h3F880000; // 17/16
            8'h43: golden = 32'h3F8C0000; // 35/32
            8'h44: golden = 32'h3F900000; // 9/8
            8'h45: golden = 32'h3F940000; // 37/32
            8'h46: golden = 32'h3F980000; // 19/16
            8'h47: golden = 32'h3F9C0000; // 39/32
            8'h48: golden = 32'h3FA00000; // 5/4
            8'h49: golden = 32'h3FA40000; // 41/32
            8'h4A: golden = 32'h3FA80000; // 21/16
            8'h4B: golden = 32'h3FAC0000; // 43/32
            8'h4C: golden = 32'h3FB00000; // 11/8
            8'h4D: golden = 32'h3FB40000; // 45/32
            8'h4E: golden = 32'h3FB80000; // 23/16
            8'h4F: golden = 32'h3FBC0000; // 47/32
            8'h50: golden = 32'h3FC00000; // 3/2
            8'h51: golden = 32'h3FC40000; // 49/32
            8'h52: golden = 32'h3FC80000; // 25/16
            8'h53: golden = 32'h3FCC0000; // 51/32
            8'h54: golden = 32'h3FD00000; // 13/8
            8'h55: golden = 32'h3FD40000; // 53/32
            8'h56: golden = 32'h3FD80000; // 27/16
            8'h57: golden = 32'h3FDC0000; // 55/32
            8'h58: golden = 32'h3FE00000; // 7/4
            8'h59: golden = 32'h3FE40000; // 57/32
            8'h5A: golden = 32'h3FE80000; // 29/16
            8'h5B: golden = 32'h3FEC0000; // 59/32
            8'h5C: golden = 32'h3FF00000; // 15/8
            8'h5D: golden = 32'h3FF40000; // 61/32
            8'h5E: golden = 32'h3FF80000; // 31/16
            8'h5F: golden = 32'h3FFC0000; // 63/32
            8'h60: golden = 32'h40000000; // 2
            8'h61: golden = 32'h40080000; // 17/8
            8'h62: golden = 32'h40100000; // 9/4
            8'h63: golden = 32'h40180000; // 19/8
            8'h64: golden = 32'h40200000; // 5/2
            8'h65: golden = 32'h40280000; // 21/8
            8'h66: golden = 32'h40300000; // 11/4
            8'h67: golden = 32'h40380000; // 23/8
            8'h68: golden = 32'h40400000; // 3
            8'h69: golden = 32'h40480000; // 25/8
            8'h6A: golden = 32'h40500000; // 13/4
            8'h6B: golden = 32'h40580000; // 27/8
            8'h6C: golden = 32'h40600000; // 7/2
            8'h6D: golden = 32'h40680000; // 29/8
            8'h6E: golden = 32'h40700000; // 15/4
            8'h6F: golden = 32'h40780000; // 31/8
            8'h70: golden = 32'h40800000; // 4
            8'h71: golden = 32'h40900000; // 9/2
            8'h72: golden = 32'h40A00000; // 5
            8'h73: golden = 32'h40B00000; // 11/2
            8'h74: golden = 32'h40C00000; // 6
            8'h75: golden = 32'h40D00000; // 13/2
            8'h76: golden = 32'h40E00000; // 7
            8'h77: golden = 32'h40F00000; // 15/2
            8'h78: golden = 32'h41000000; // 8
            8'h79: golden = 32'h41200000; // 10
            8'h7A: golden = 32'h41400000; // 12
            8'h7B: golden = 32'h41600000; // 14
            8'h7C: golden = 32'h41800000; // 16
            8'h7D: golden = 32'h41C00000; // 24
            8'h7E: golden = 32'h42000000; // 32
            8'h7F: golden = 32'h42800000; // 64
            8'h80: golden = 32'h7FC00000; // NaR (qNaN)
            8'h81: golden = 32'hC2800000; // -64
            8'h82: golden = 32'hC2000000; // -32
            8'h83: golden = 32'hC1C00000; // -24
            8'h84: golden = 32'hC1800000; // -16
            8'h85: golden = 32'hC1600000; // -14
            8'h86: golden = 32'hC1400000; // -12
            8'h87: golden = 32'hC1200000; // -10
            8'h88: golden = 32'hC1000000; // -8
            8'h89: golden = 32'hC0F00000; // -15/2
            8'h8A: golden = 32'hC0E00000; // -7
            8'h8B: golden = 32'hC0D00000; // -13/2
            8'h8C: golden = 32'hC0C00000; // -6
            8'h8D: golden = 32'hC0B00000; // -11/2
            8'h8E: golden = 32'hC0A00000; // -5
            8'h8F: golden = 32'hC0900000; // -9/2
            8'h90: golden = 32'hC0800000; // -4
            8'h91: golden = 32'hC0780000; // -31/8
            8'h92: golden = 32'hC0700000; // -15/4
            8'h93: golden = 32'hC0680000; // -29/8
            8'h94: golden = 32'hC0600000; // -7/2
            8'h95: golden = 32'hC0580000; // -27/8
            8'h96: golden = 32'hC0500000; // -13/4
            8'h97: golden = 32'hC0480000; // -25/8
            8'h98: golden = 32'hC0400000; // -3
            8'h99: golden = 32'hC0380000; // -23/8
            8'h9A: golden = 32'hC0300000; // -11/4
            8'h9B: golden = 32'hC0280000; // -21/8
            8'h9C: golden = 32'hC0200000; // -5/2
            8'h9D: golden = 32'hC0180000; // -19/8
            8'h9E: golden = 32'hC0100000; // -9/4
            8'h9F: golden = 32'hC0080000; // -17/8
            8'hA0: golden = 32'hC0000000; // -2
            8'hA1: golden = 32'hBFFC0000; // -63/32
            8'hA2: golden = 32'hBFF80000; // -31/16
            8'hA3: golden = 32'hBFF40000; // -61/32
            8'hA4: golden = 32'hBFF00000; // -15/8
            8'hA5: golden = 32'hBFEC0000; // -59/32
            8'hA6: golden = 32'hBFE80000; // -29/16
            8'hA7: golden = 32'hBFE40000; // -57/32
            8'hA8: golden = 32'hBFE00000; // -7/4
            8'hA9: golden = 32'hBFDC0000; // -55/32
            8'hAA: golden = 32'hBFD80000; // -27/16
            8'hAB: golden = 32'hBFD40000; // -53/32
            8'hAC: golden = 32'hBFD00000; // -13/8
            8'hAD: golden = 32'hBFCC0000; // -51/32
            8'hAE: golden = 32'hBFC80000; // -25/16
            8'hAF: golden = 32'hBFC40000; // -49/32
            8'hB0: golden = 32'hBFC00000; // -3/2
            8'hB1: golden = 32'hBFBC0000; // -47/32
            8'hB2: golden = 32'hBFB80000; // -23/16
            8'hB3: golden = 32'hBFB40000; // -45/32
            8'hB4: golden = 32'hBFB00000; // -11/8
            8'hB5: golden = 32'hBFAC0000; // -43/32
            8'hB6: golden = 32'hBFA80000; // -21/16
            8'hB7: golden = 32'hBFA40000; // -41/32
            8'hB8: golden = 32'hBFA00000; // -5/4
            8'hB9: golden = 32'hBF9C0000; // -39/32
            8'hBA: golden = 32'hBF980000; // -19/16
            8'hBB: golden = 32'hBF940000; // -37/32
            8'hBC: golden = 32'hBF900000; // -9/8
            8'hBD: golden = 32'hBF8C0000; // -35/32
            8'hBE: golden = 32'hBF880000; // -17/16
            8'hBF: golden = 32'hBF840000; // -33/32
            8'hC0: golden = 32'hBF800000; // -1
            8'hC1: golden = 32'hBF7C0000; // -63/64
            8'hC2: golden = 32'hBF780000; // -31/32
            8'hC3: golden = 32'hBF740000; // -61/64
            8'hC4: golden = 32'hBF700000; // -15/16
            8'hC5: golden = 32'hBF6C0000; // -59/64
            8'hC6: golden = 32'hBF680000; // -29/32
            8'hC7: golden = 32'hBF640000; // -57/64
            8'hC8: golden = 32'hBF600000; // -7/8
            8'hC9: golden = 32'hBF5C0000; // -55/64
            8'hCA: golden = 32'hBF580000; // -27/32
            8'hCB: golden = 32'hBF540000; // -53/64
            8'hCC: golden = 32'hBF500000; // -13/16
            8'hCD: golden = 32'hBF4C0000; // -51/64
            8'hCE: golden = 32'hBF480000; // -25/32
            8'hCF: golden = 32'hBF440000; // -49/64
            8'hD0: golden = 32'hBF400000; // -3/4
            8'hD1: golden = 32'hBF3C0000; // -47/64
            8'hD2: golden = 32'hBF380000; // -23/32
            8'hD3: golden = 32'hBF340000; // -45/64
            8'hD4: golden = 32'hBF300000; // -11/16
            8'hD5: golden = 32'hBF2C0000; // -43/64
            8'hD6: golden = 32'hBF280000; // -21/32
            8'hD7: golden = 32'hBF240000; // -41/64
            8'hD8: golden = 32'hBF200000; // -5/8
            8'hD9: golden = 32'hBF1C0000; // -39/64
            8'hDA: golden = 32'hBF180000; // -19/32
            8'hDB: golden = 32'hBF140000; // -37/64
            8'hDC: golden = 32'hBF100000; // -9/16
            8'hDD: golden = 32'hBF0C0000; // -35/64
            8'hDE: golden = 32'hBF080000; // -17/32
            8'hDF: golden = 32'hBF040000; // -33/64
            8'hE0: golden = 32'hBF000000; // -1/2
            8'hE1: golden = 32'hBEF80000; // -31/64
            8'hE2: golden = 32'hBEF00000; // -15/32
            8'hE3: golden = 32'hBEE80000; // -29/64
            8'hE4: golden = 32'hBEE00000; // -7/16
            8'hE5: golden = 32'hBED80000; // -27/64
            8'hE6: golden = 32'hBED00000; // -13/32
            8'hE7: golden = 32'hBEC80000; // -25/64
            8'hE8: golden = 32'hBEC00000; // -3/8
            8'hE9: golden = 32'hBEB80000; // -23/64
            8'hEA: golden = 32'hBEB00000; // -11/32
            8'hEB: golden = 32'hBEA80000; // -21/64
            8'hEC: golden = 32'hBEA00000; // -5/16
            8'hED: golden = 32'hBE980000; // -19/64
            8'hEE: golden = 32'hBE900000; // -9/32
            8'hEF: golden = 32'hBE880000; // -17/64
            8'hF0: golden = 32'hBE800000; // -1/4
            8'hF1: golden = 32'hBE700000; // -15/64
            8'hF2: golden = 32'hBE600000; // -7/32
            8'hF3: golden = 32'hBE500000; // -13/64
            8'hF4: golden = 32'hBE400000; // -3/16
            8'hF5: golden = 32'hBE300000; // -11/64
            8'hF6: golden = 32'hBE200000; // -5/32
            8'hF7: golden = 32'hBE100000; // -9/64
            8'hF8: golden = 32'hBE000000; // -1/8
            8'hF9: golden = 32'hBDE00000; // -7/64
            8'hFA: golden = 32'hBDC00000; // -3/32
            8'hFB: golden = 32'hBDA00000; // -5/64
            8'hFC: golden = 32'hBD800000; // -1/16
            8'hFD: golden = 32'hBD400000; // -3/64
            8'hFE: golden = 32'hBD000000; // -1/32
            8'hFF: golden = 32'hBC800000; // -1/64
        endcase
    end

    // Primary: DUT output must match golden for ALL 256 inputs
    always @(*) begin
        assert(fp32_out == golden);
        assert(is_zero == (posit_in == 8'h00));
        assert(is_nar  == (posit_in == 8'h80));
    end

    // Sign: negative posit → negative FP32 (except zero/NaR)
    always @(*) begin
        if (posit_in[7] && posit_in != 8'h80)
            assert(fp32_out[31] == 1'b1);
        if (!posit_in[7] && posit_in != 8'h00)
            assert(fp32_out[31] == 1'b0);
    end

    // Symmetry: posit(n) == -posit(256-n) for n in [1,127]
    // (encoded via golden LUT — if both entries are correct, symmetry holds)
endmodule
