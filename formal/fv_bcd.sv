// Formal verification: BCD → binary decode
// Verifies arithmetic (tens*10 + ones) and validity flag
`default_nettype none

module fv_bcd;
    (* anyconst *) wire [7:0] bcd_in;
    wire [6:0] bin_out;
    wire       valid;

    bcd_decode dut (.bcd_in(bcd_in), .bin_out(bin_out), .valid(valid));

    wire [3:0] tens = bcd_in[7:4];
    wire [3:0] ones = bcd_in[3:0];

    // Independent golden: tens*10 + ones using multiplication
    wire [7:0] golden_full = ({4'b0, tens} * 8'd10) + {4'b0, ones};
    wire [6:0] golden = golden_full[6:0];

    always @(*) begin
        assert(bin_out == golden);
        assert(valid == (tens <= 4'd9 && ones <= 4'd9));
        // Valid BCD range: output is 0-99
        if (valid) assert(bin_out <= 7'd99);
        // Known values
        if (bcd_in == 8'h00) assert(bin_out == 7'd0);
        if (bcd_in == 8'h42) assert(bin_out == 7'd42);
        if (bcd_in == 8'h99) assert(bin_out == 7'd99);

        cover(bcd_in == 8'h00);  // 0
        cover(bcd_in == 8'h42);  // 42
        cover(bcd_in == 8'h99);  // 99 (max valid)
        cover(bcd_in == 8'hAA);  // invalid BCD
    end
endmodule
