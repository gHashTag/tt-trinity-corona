// Exhaustive ROM golden validation — all 80 records, first 4 bytes each.
// Verifies ROM content through synthesized netlist against format_rom.v.
// Usage: yosys -> synth_netlist.v, then iverilog + simcells.v + this file.
`timescale 1ns/1ps

module tb_rom_golden;
    reg        clk = 0;
    reg        rst_n = 0;
    reg        ena = 1;
    reg  [7:0] ui_in = 8'h80;
    reg  [7:0] uio_in = 8'h00;
    wire [7:0] uo_out, uio_out, uio_oe;

    tt_um_trinity_corona dut (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .ui_in(ui_in), .uo_out(uo_out),
        .uio_in(uio_in), .uio_out(uio_out), .uio_oe(uio_oe)
    );

    always #10 clk = ~clk;

    integer errors = 0;
    integer i;
    integer pre_err;

    // Golden: first 4 readback bytes {byte3, byte2, byte1, byte0} for each record.
    // Derived from format_rom.v rom_data[31:0] (LSB-first readback).
    reg [31:0] golden [0:79];

    initial begin
        golden[ 0] = 32'h1E370000;
        golden[ 1] = 32'h452C0100;
        golden[ 2] = 32'h68100200;
        golden[ 3] = 32'h7BEE0300;
        golden[ 4] = 32'h899B0400;
        golden[ 5] = 32'h37D10500;
        golden[ 6] = 32'h75410600;
        golden[ 7] = 32'h8B990700;
        golden[ 8] = 32'h865A0801;
        golden[ 9] = 32'h2E950901;
        golden[10] = 32'hFFFF0A01;
        golden[11] = 32'hB71D0B01;
        golden[12] = 32'hE1C80C01;
        golden[13] = 32'hFFFF0D01;
        golden[14] = 32'hB71D0E01;
        golden[15] = 32'h1E370F06;
        golden[16] = 32'h0C730F06;
        golden[17] = 32'h21C80F06;
        golden[18] = 32'h1E370F06;
        golden[19] = 32'h0BEE0F06;
        golden[20] = 32'h01C80F06;
        golden[21] = 32'h1E370F06;
        golden[22] = 32'h08E20F06;
        golden[23] = 32'h15AE0F06;
        golden[24] = 32'h116A0F06;
        golden[25] = 32'h1A160F06;
        golden[26] = 32'h14D90F06;
        golden[27] = 32'h15F50F06;
        golden[28] = 32'h16810F06;
        golden[29] = 32'h17510F06;
        golden[30] = 32'h9E370F06;
        golden[31] = 32'hFFFF1001;
        golden[32] = 32'hFFFF1006;
        golden[33] = 32'hFFFF1100;
        golden[34] = 32'hFFFF1100;
        golden[35] = 32'hFFFF1208;
        golden[36] = 32'hFFFF1208;
        golden[37] = 32'hFFFF1208;
        golden[38] = 32'hFFFF1208;
        golden[39] = 32'hB71D1301;
        golden[40] = 32'hE1C81301;
        golden[41] = 32'hFFFF1301;
        golden[42] = 32'h21C81401;
        golden[43] = 32'h1E371400;
        golden[44] = 32'h452C1500;
        golden[45] = 32'h452C1600;
        golden[46] = 32'h9E371707;
        golden[47] = 32'h9E371707;
        golden[48] = 32'h9E371700;
        golden[49] = 32'h9E371700;
        golden[50] = 32'h9E371700;
        golden[51] = 32'h9E371800;
        golden[52] = 32'h9E371800;
        golden[53] = 32'h9E371901;
        golden[54] = 32'h452C1A00;
        golden[55] = 32'h78FA1A00;
        golden[56] = 32'h538C1B00;
        golden[57] = 32'h7E371B00;
        golden[58] = 32'h4E371C00;
        golden[59] = 32'h452C1D00;
        golden[60] = 32'h78FA1D00;
        golden[61] = 32'h452C1E00;
        golden[62] = 32'h62371F00;
        golden[63] = 32'h69B42000;
        golden[64] = 32'hFFFF2100;
        golden[65] = 32'hFFFF2200;
        golden[66] = 32'h452C2300;
        golden[67] = 32'h452C2400;
        golden[68] = 32'h1E372500;
        golden[69] = 32'hB71D2601;
        golden[70] = 32'h9E372701;
        golden[71] = 32'h9E372807;
        golden[72] = 32'h7BEE2900;
        golden[73] = 32'hFFFF2A00;
        golden[74] = 32'h83232B00;
        golden[75] = 32'h9E372C01;
        golden[76] = 32'h9E372D00;
        golden[77] = 32'h0C730C01;
        golden[78] = 32'hFFFF1301;
        golden[79] = 32'h9E371301;
    end

    task rom_check(input [6:0] addr, input [31:0] exp, input integer idx);
    begin
        pre_err = errors;
        ui_in = {1'b0, addr};
        @(posedge clk); #1;
        ui_in = 8'h00;
        @(posedge clk); #1;
        ui_in = 8'h80;
        if (uo_out !== exp[7:0]) begin
            $display("FAIL: rom[%0d] b0 got=%02X exp=%02X", idx, uo_out, exp[7:0]);
            errors = errors + 1;
        end
        @(posedge clk); #1;
        if (uo_out !== exp[15:8]) begin
            $display("FAIL: rom[%0d] b1 got=%02X exp=%02X", idx, uo_out, exp[15:8]);
            errors = errors + 1;
        end
        @(posedge clk); #1;
        if (uo_out !== exp[23:16]) begin
            $display("FAIL: rom[%0d] b2 got=%02X exp=%02X", idx, uo_out, exp[23:16]);
            errors = errors + 1;
        end
        @(posedge clk); #1;
        if (uo_out !== exp[31:24]) begin
            $display("FAIL: rom[%0d] b3 got=%02X exp=%02X", idx, uo_out, exp[31:24]);
            errors = errors + 1;
        end
        if (errors == pre_err) $display("PASS: rom[%0d]", idx);
        repeat(8) begin @(posedge clk); #1; end
    end
    endtask

    reg [6:0] addr_val;

    initial begin
        #100;
        rst_n = 1;
        @(posedge clk); #1;

        for (i = 0; i < 80; i = i + 1) begin
            addr_val = i[6:0];
            rom_check(addr_val, golden[i], i);
        end

        @(posedge clk);
        if (errors == 0)
            $display("ROM GOLDEN: ALL 80 RECORDS PASS");
        else
            $display("ROM GOLDEN: %0d FAILURES", errors);
        $finish;
    end

    initial begin
        $dumpfile("tb_rom_golden.vcd");
        $dumpvars(0, tb_rom_golden);
    end
endmodule
