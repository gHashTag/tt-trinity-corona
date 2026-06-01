// Formal verification: LNS8 antilog decode
// Verifies LUT correctness and shift logic for 2^(Q3.4) computation
`default_nettype none

module fv_lns8;
    (* anyconst *) wire [7:0] lns_in;
    wire        sign_out;
    wire [15:0] magnitude;
    wire        is_zero;

    lns8_decode dut (
        .lns_in(lns_in), .sign_out(sign_out),
        .magnitude(magnitude), .is_zero(is_zero)
    );

    wire [6:0] log_val = lns_in[6:0];
    wire [2:0] int_part  = log_val[6:4];
    wire [3:0] frac_part = log_val[3:0];

    // Independent LUT (2^(frac/16) * 256, rounded)
    reg [8:0] golden_lut;
    always @(*) begin
        case (frac_part)
            4'd0:  golden_lut = 9'd256;
            4'd1:  golden_lut = 9'd267;
            4'd2:  golden_lut = 9'd279;
            4'd3:  golden_lut = 9'd291;
            4'd4:  golden_lut = 9'd304;
            4'd5:  golden_lut = 9'd317;
            4'd6:  golden_lut = 9'd331;
            4'd7:  golden_lut = 9'd345;
            4'd8:  golden_lut = 9'd362;
            4'd9:  golden_lut = 9'd378;
            4'd10: golden_lut = 9'd395;
            4'd11: golden_lut = 9'd412;
            4'd12: golden_lut = 9'd431;
            4'd13: golden_lut = 9'd450;
            4'd14: golden_lut = 9'd470;
            4'd15: golden_lut = 9'd490;
        endcase
    end

    wire [15:0] golden_mag = is_zero ? 16'h0000 : ({7'b0, golden_lut} << int_part);

    always @(*) begin
        assert(sign_out == lns_in[7]);
        assert(is_zero == (lns_in == 8'h00));
        assert(magnitude == golden_mag);
        // Zero input → zero magnitude
        if (lns_in == 8'h00) assert(magnitude == 16'h0000);
        // Minimum positive: lns_in=0x01, log=0.0625, 2^0.0625 ≈ 1.044
        // int=0, frac=1, lut=267, shift=0 → magnitude=267
        if (lns_in == 8'h01) assert(magnitude == 16'd267);
        // log_val=0x40 (int=4, frac=0): 2^4=16, magnitude = 256<<4 = 4096
        if (lns_in[6:0] == 7'h40 && lns_in != 8'h00)
            assert(magnitude == 16'd4096);
    end
endmodule
