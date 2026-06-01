// Formal verification: INT4 sign-extension decode
`default_nettype none

module fv_int4;
    (* anyconst *) wire [3:0] int4_in;
    wire [31:0] int32_out;
    wire        is_zero;

    int4_decode dut (.int4_in(int4_in), .int32_out(int32_out), .is_zero(is_zero));

    wire [31:0] golden = {{28{int4_in[3]}}, int4_in};

    always @(*) begin
        assert(int32_out == golden);
        assert(is_zero == (int4_in == 4'd0));
        if (!int4_in[3]) assert(int32_out[31:4] == 28'd0);
        if (int4_in[3])  assert(int32_out[31:4] == {28{1'b1}});
    end
endmodule
