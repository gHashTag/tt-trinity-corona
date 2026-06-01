// Formal verification: INT8 sign-extension decode
`default_nettype none

module fv_int8;
    (* anyconst *) wire [7:0] int8_in;
    wire [31:0] int32_out;
    wire        is_zero;

    int8_decode dut (.int8_in(int8_in), .int32_out(int32_out), .is_zero(is_zero));

    // Golden: sign-extend bit 7 across upper 24 bits
    wire [31:0] golden = {{24{int8_in[7]}}, int8_in};

    always @(*) begin
        assert(int32_out == golden);
        assert(is_zero == (int8_in == 8'd0));
        // Structural: positive inputs produce positive outputs
        if (!int8_in[7]) assert(int32_out[31] == 1'b0);
        if (int8_in[7])  assert(int32_out[31] == 1'b1);

        cover(int8_in == 8'd0);    // zero
        cover(int8_in == 8'd127);  // max positive
        cover(int8_in == 8'h80);   // min negative (-128)
        cover(int8_in == 8'hFF);   // -1
    end
endmodule
