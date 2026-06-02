// SPDX-License-Identifier: Apache-2.0
// test/tb_posit8_sweep.v
// Loop 87: exhaustive 256-value sweep of posit8_decode for independent
// verification against a from-scratch Posit-Standard reference (see
// test/test_posit8_independent.py). Prints "<index> <fp32_hex>" per line.
`timescale 1ns/1ps

module tb_posit8_sweep;
    reg  [7:0]  in;
    wire [31:0] out;
    wire        iz, inar;

    posit8_decode dut (
        .posit_in(in), .fp32_out(out), .is_zero(iz), .is_nar(inar)
    );

    integer i;
    initial begin
        for (i = 0; i < 256; i = i + 1) begin
            in = i[7:0];
            #1;
            $display("%0d %08h", i, out);
        end
        $finish;
    end
endmodule
