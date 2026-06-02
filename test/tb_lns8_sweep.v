// SPDX-License-Identifier: Apache-2.0
// test/tb_lns8_sweep.v
// Loop 88: exhaustive 256-value sweep of lns8_decode for independent
// verification (see test/test_lns8_independent.py).
// Prints "<index> <sign> <magnitude> <is_zero>" per line.
`timescale 1ns/1ps

module tb_lns8_sweep;
    reg  [7:0]  in;
    wire        s, iz;
    wire [15:0] mag;

    lns8_decode dut (
        .lns_in(in), .sign_out(s), .magnitude(mag), .is_zero(iz)
    );

    integer i;
    initial begin
        for (i = 0; i < 256; i = i + 1) begin
            in = i[7:0];
            #1;
            $display("%0d %0d %0d %0d", i, s, mag, iz);
        end
        $finish;
    end
endmodule
