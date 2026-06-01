// SPDX-License-Identifier: Apache-2.0
// Formal verification of format_rom -- SSOT catalog integrity.
// Verifies: self-index, default-zero, non-zero, exhaustive 80-entry golden LUT,
//           field-range bounds, cross-field consistency.
`default_nettype none

module fv_rom (
    input wire clk
);
    (* anyconst *) reg [6:0] addr;
    wire [79:0] data;

    format_rom uut (.clk(clk), .addr(addr), .data(data));

    reg f_past_valid = 1'b0;
    always @(posedge clk) f_past_valid <= 1'b1;

    // ---------------------------------------------------------------
    // Field extraction (matches specs/corona/rom_layout.t27)
    // ---------------------------------------------------------------
    wire [7:0]  f_format_index = data[79:72];
    wire [3:0]  f_cluster_id   = data[71:68];
    wire [3:0]  f_status_id    = data[67:64];
    wire [7:0]  f_total_bits   = data[63:56];
    wire [3:0]  f_sign_bits    = data[55:52];
    wire [7:0]  f_exp_bits     = data[51:44];
    wire [7:0]  f_mant_bits    = data[43:36];
    wire [3:0]  f_enc_kind     = data[35:32];
    wire [15:0] f_phi_dist     = data[31:16];
    wire [7:0]  f_ref_index    = data[15:8];
    wire [7:0]  f_flags        = data[7:0];

    always @(posedge clk) if (f_past_valid) begin

        // ===========================================================
        // P1-P3: Structural invariants (original)
        // ===========================================================

        // P1: Self-index -- MSB byte of every record equals its address
        if (addr <= 7'd79) assert(data[79:72] == {1'b0, addr});

        // P2: Default zero for out-of-range addresses (80-127)
        if (addr > 7'd79) assert(data == 80'h0);

        // P3: Non-zero for all valid addresses
        if (addr <= 7'd79) assert(data != 80'h0);

        // ===========================================================
        // P4: Exhaustive golden LUT -- all 80 records verified
        // ===========================================================
        case (addr)
            7'd 0: assert(data == 80'h0007101050A01E370000);
            7'd 1: assert(data == 80'h010720108170452C0100);
            7'd 2: assert(data == 80'h02074010B34068100200);
            7'd 3: assert(data == 80'h03078010F7007BEE0300);
            7'd 4: assert(data == 80'h040700113EC0899B0400);
            7'd 5: assert(data == 80'h05172010814437D10500);
            7'd 6: assert(data == 80'h06174010832475410600);
            7'd 7: assert(data == 80'h0717801086E48B990700);
            7'd 8: assert(data == 80'h082710108070865A0801);
            7'd 9: assert(data == 80'h0927201080A02E950901);
            7'd10: assert(data == 80'h0A2508105020FFFF0A01);
            7'd11: assert(data == 80'h0B2508104030B71D0B01);
            7'd12: assert(data == 80'h0C2706103020E1C80C01);
            7'd13: assert(data == 80'h0D2704102010FFFF0D01);
            7'd14: assert(data == 80'h0E2508104030B71D0E01);
            7'd15: assert(data == 80'h0F32041010271E370F06);
            7'd16: assert(data == 80'h1032061020370C730F06);
            7'd17: assert(data == 80'h11320810304721C80F06);
            7'd18: assert(data == 80'h12320A1030671E370F06);
            7'd19: assert(data == 80'h13320C1040770BEE0F06);
            7'd20: assert(data == 80'h14320E10508701C80F06);
            7'd21: assert(data == 80'h1532101050A71E370F06);
            7'd22: assert(data == 80'h1632141070C708E20F06);
            7'd23: assert(data == 80'h1732181080F715AE0F06);
            7'd24: assert(data == 80'h18322010B147116A0F06);
            7'd25: assert(data == 80'h1932301101F71A160F06);
            7'd26: assert(data == 80'h1A324011629714D90F06);
            7'd27: assert(data == 80'h1B32601213E715F50F06);
            7'd28: assert(data == 80'h1C328012C53716810F06);
            7'd29: assert(data == 80'h1D3200158A7717510F06);
            7'd30: assert(data == 80'h1E32021000179E370F06);
            7'd31: assert(data == 80'h1F4508100001FFFF1001);
            7'd32: assert(data == 80'h204510101001FFFF1006);
            7'd33: assert(data == 80'h214520102001FFFF1100);
            7'd34: assert(data == 80'h224540103001FFFF1100);
            7'd35: assert(data == 80'h234508100006FFFF1208);
            7'd36: assert(data == 80'h244510100006FFFF1208);
            7'd37: assert(data == 80'h254520100006FFFF1208);
            7'd38: assert(data == 80'h264540100006FFFF1208);
            7'd39: assert(data == 80'h275708104035B71D1301);
            7'd40: assert(data == 80'h285706103025E1C81301);
            7'd41: assert(data == 80'h295704102015FFFF1301);
            7'd42: assert(data == 80'h2A650810304221C81401);
            7'd43: assert(data == 80'h2B65101050A21E371400);
            7'd44: assert(data == 80'h2C6520108172452C1500);
            7'd45: assert(data == 80'h2D6520108172452C1600);
            7'd46: assert(data == 80'h2E77041000339E371707);
            7'd47: assert(data == 80'h2F77081000739E371707);
            7'd48: assert(data == 80'h3077101000F39E371700);
            7'd49: assert(data == 80'h3177201001F39E371700);
            7'd50: assert(data == 80'h3277401003F39E371700);
            7'd51: assert(data == 80'h3377040000439E371800);
            7'd52: assert(data == 80'h3477101000F39E371800);
            7'd53: assert(data == 80'h3577080000849E371901);
            7'd54: assert(data == 80'h368620108178452C1A00);
            7'd55: assert(data == 80'h37864010837878FA1A00);
            7'd56: assert(data == 80'h388620107188538C1B00);
            7'd57: assert(data == 80'h3986401073887E371B00);
            7'd58: assert(data == 80'h3A864010F3084E371C00);
            7'd59: assert(data == 80'h3B8620108178452C1D00);
            7'd60: assert(data == 80'h3C864010837878FA1D00);
            7'd61: assert(data == 80'h3D8620108178452C1E00);
            7'd62: assert(data == 80'h3E865010F40862371F00);
            7'd63: assert(data == 80'h3F863010827869B42000);
            7'd64: assert(data == 80'h409720100009FFFF2100);
            7'd65: assert(data == 80'h419720100009FFFF2200);
            7'd66: assert(data == 80'h429220108179452C2300);
            7'd67: assert(data == 80'h439220108179452C2400);
            7'd68: assert(data == 80'h44A7101050A01E372500);
            7'd69: assert(data == 80'h45A508104030B71D2601);
            7'd70: assert(data == 80'h46A5040000439E372701);
            7'd71: assert(data == 80'h47A5021000139E372807);
            7'd72: assert(data == 80'h48B78010F7007BEE2900);
            7'd73: assert(data == 80'h49B580107001FFFF2A00);
            7'd74: assert(data == 80'h4AB18010B68083232B00);
            7'd75: assert(data == 80'h4BC5040000439E372C01);
            7'd76: assert(data == 80'h4CC5040000439E372D00);
            7'd77: assert(data == 80'h4D27061020300C730C01);
            7'd78: assert(data == 80'h4E5708008005FFFF1301);
            7'd79: assert(data == 80'h4F57081000759E371301);
            default: begin end
        endcase

        // ===========================================================
        // P6: Field-range assertions (valid addresses only)
        //     Derived from exhaustive analysis of all 80 records.
        // ===========================================================
        if (addr <= 7'd79) begin

            // cluster_id in [0..12]
            assert(f_cluster_id <= 4'd12);

            // status_id in {1, 2, 5, 6, 7} -- never 0, 3, 4, 8..15
            assert(f_status_id == 4'd1 ||
                   f_status_id == 4'd2 ||
                   f_status_id == 4'd5 ||
                   f_status_id == 4'd6 ||
                   f_status_id == 4'd7);

            // total_bits: only specific powers-of-2 and even values appear.
            // Observed: {0,2,4,6,8,10,12,14,16,20,24,32,48,64,80,96,128}
            // All values are even (bit 0 always 0).
            assert(f_total_bits[0] == 1'b0);

            // total_bits <= 128
            assert(f_total_bits <= 8'd128);

            // sign_bits in {0, 1}
            assert(f_sign_bits <= 4'd1);

            // exp_bits <= 88
            assert(f_exp_bits <= 8'd88);

            // mant_bits <= 236
            assert(f_mant_bits <= 8'd236);

            // encoding_kind in [0..9]
            assert(f_enc_kind <= 4'd9);

            // phi_distance >= 456 (0x01C8, minimum observed at addr 20)
            assert(f_phi_dist >= 16'h01C8);

            // ref_index <= 45 (maximum observed across all 80 records)
            assert(f_ref_index <= 8'd45);

            // flags in {0, 1, 6, 7, 8}
            assert(f_flags == 8'd0 ||
                   f_flags == 8'd1 ||
                   f_flags == 8'd6 ||
                   f_flags == 8'd7 ||
                   f_flags == 8'd8);
        end

        // ===========================================================
        // P7: Cross-field consistency rules (valid addresses only)
        // ===========================================================
        if (addr <= 7'd79) begin

            // R1: Fixed-point (enc_kind==3) must have exp_bits==0
            if (f_enc_kind == 4'd3) assert(f_exp_bits == 8'd0);

            // R2: Fixed-point (enc_kind==3) with sign: sign+mant==total
            if (f_enc_kind == 4'd3)
                assert(f_sign_bits + f_mant_bits == f_total_bits);

            // R3: Decimal-float (enc_kind==8) always has sign_bits==1
            if (f_enc_kind == 4'd8) assert(f_sign_bits == 4'd1);

            // R4: Decimal-float (enc_kind==8): s+e+m == total
            if (f_enc_kind == 4'd8)
                assert(f_sign_bits + f_exp_bits + f_mant_bits == f_total_bits);

            // R5: Log-number (enc_kind==2) always has sign_bits==1
            if (f_enc_kind == 4'd2) assert(f_sign_bits == 4'd1);

            // R6: Log-number (enc_kind==2): s+e+m == total
            if (f_enc_kind == 4'd2)
                assert(f_sign_bits + f_exp_bits + f_mant_bits == f_total_bits);

            // R7: Posit-family (enc_kind==7): sign_bits==1 always
            if (f_enc_kind == 4'd7) assert(f_sign_bits == 4'd1);

            // R8: Cluster 3 (posit sweep, all enc_kind==7): flags==6, ref_index==15
            if (f_cluster_id == 4'd3) begin
                assert(f_enc_kind == 4'd7);
                assert(f_flags == 8'd6);
                assert(f_ref_index == 8'd15);
            end

            // R9: Cluster 8 (decimal-float): enc_kind==8, status_id==6
            if (f_cluster_id == 4'd8) begin
                assert(f_enc_kind == 4'd8);
                assert(f_status_id == 4'd6);
            end

            // R10: Cluster 4 (integer/fixed): enc_kind in {1,6}, status_id==5
            if (f_cluster_id == 4'd4) begin
                assert(f_enc_kind == 4'd1 || f_enc_kind == 4'd6);
                assert(f_status_id == 4'd5);
            end

            // R11: ref_index always points to a valid record (0..79)
            assert(f_ref_index <= 8'd79);

            // R12: All encoding_kind==6 records have sign=1, exp=0, mant=0
            if (f_enc_kind == 4'd6) begin
                assert(f_sign_bits == 4'd1);
                assert(f_exp_bits == 8'd0);
                assert(f_mant_bits == 8'd0);
            end

            // R13: All encoding_kind==1 records have mant_bits==0
            if (f_enc_kind == 4'd1) assert(f_mant_bits == 8'd0);
        end

        // ===========================================================
        // P8: Cover properties -- verify the proof exercises key entries
        // ===========================================================
        cover(addr == 7'd 0);   // first entry (fp16)
        cover(addr == 7'd79);   // last entry
        cover(addr == 7'd80);   // first out-of-range (default zero)
        cover(f_cluster_id == 4'd3);   // posit cluster
        cover(f_cluster_id == 4'd8);   // decimal-float cluster
        cover(f_enc_kind == 4'd6);     // unsigned integer encoding
        cover(f_enc_kind == 4'd7);     // posit encoding
        cover(f_status_id == 4'd6);    // historical status

    end
endmodule
