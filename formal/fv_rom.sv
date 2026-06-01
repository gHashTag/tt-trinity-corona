// Formal verification of format_rom -- SSOT catalog integrity.
// Proves: self-index, default-zero, non-zero, golden spot-checks,
//         field-range bounds, cross-field consistency.
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
        // P4: Golden spot-checks -- original 3 (first, middle, last)
        // ===========================================================
        if (addr == 7'd 0) assert(data == 80'h0007101050A01E370000);
        if (addr == 7'd40) assert(data == 80'h285706103025E1C81301);
        if (addr == 7'd79) assert(data == 80'h4F57081000759E371301);

        // ===========================================================
        // P5: Additional golden spot-checks -- one per uncovered cluster
        //     Covered by P4: cluster 0 (addr 0), cluster 5 (addr 40,79)
        // ===========================================================

        // Cluster 1 (bfloat-family): addr 6
        if (addr == 7'd 6) assert(data == 80'h06174010832475410600);

        // Cluster 2 (mini-float/IEEE sub-byte): addr 12
        if (addr == 7'd12) assert(data == 80'h0C2706103020E1C80C01);

        // Cluster 3 (posit-family sweep): addr 23
        if (addr == 7'd23) assert(data == 80'h1732181080F715AE0F06);

        // Cluster 4 (integer/fixed): addr 35
        if (addr == 7'd35) assert(data == 80'h234508100006FFFF1208);

        // Cluster 6 (log-number): addr 44
        if (addr == 7'd44) assert(data == 80'h2C6520108172452C1500);

        // Cluster 7 (fixed-point/block): addr 50
        if (addr == 7'd50) assert(data == 80'h3277401003F39E371700);

        // Cluster 8 (decimal-float): addr 59
        if (addr == 7'd59) assert(data == 80'h3B8620108178452C1D00);

        // Cluster 9 (quantized/stochastic): addr 66
        if (addr == 7'd66) assert(data == 80'h429220108179452C2300);

        // Cluster 10 (legacy oddball): addr 70
        if (addr == 7'd70) assert(data == 80'h46A5040000439E372701);

        // Cluster 11 (extended-precision): addr 73
        if (addr == 7'd73) assert(data == 80'h49B580107001FFFF2A00);

        // Cluster 12 (custom ultra-narrow): addr 76
        if (addr == 7'd76) assert(data == 80'h4CC5040000439E372D00);

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

    end
endmodule
