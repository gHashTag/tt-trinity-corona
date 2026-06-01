// Exhaustive ROM golden validation — all 80 records, full 10 bytes each.
// Verifies complete ROM content through synthesized netlist against format_rom.v.
// 800 byte-level assertions total (80 records x 10 bytes).
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
    integer i, b;
    integer pre_err;

    // Golden ROM bytes: 10 bytes per record, stored as {lo[31:0], mid[31:0], hi[15:0]}
    // Readback order: byte[0]=rom_data[7:0], ..., byte[9]=rom_data[79:72]
    reg [31:0] golden_lo  [0:79];
    reg [31:0] golden_mid [0:79];
    reg [15:0] golden_hi  [0:79];

    initial begin
        golden_lo[ 0] = 32'h1E370000; golden_mid[ 0] = 32'h101050A0; golden_hi[ 0] = 16'h0007;
        golden_lo[ 1] = 32'h452C0100; golden_mid[ 1] = 32'h20108170; golden_hi[ 1] = 16'h0107;
        golden_lo[ 2] = 32'h68100200; golden_mid[ 2] = 32'h4010B340; golden_hi[ 2] = 16'h0207;
        golden_lo[ 3] = 32'h7BEE0300; golden_mid[ 3] = 32'h8010F700; golden_hi[ 3] = 16'h0307;
        golden_lo[ 4] = 32'h899B0400; golden_mid[ 4] = 32'h00113EC0; golden_hi[ 4] = 16'h0407;
        golden_lo[ 5] = 32'h37D10500; golden_mid[ 5] = 32'h20108144; golden_hi[ 5] = 16'h0517;
        golden_lo[ 6] = 32'h75410600; golden_mid[ 6] = 32'h40108324; golden_hi[ 6] = 16'h0617;
        golden_lo[ 7] = 32'h8B990700; golden_mid[ 7] = 32'h801086E4; golden_hi[ 7] = 16'h0717;
        golden_lo[ 8] = 32'h865A0801; golden_mid[ 8] = 32'h10108070; golden_hi[ 8] = 16'h0827;
        golden_lo[ 9] = 32'h2E950901; golden_mid[ 9] = 32'h201080A0; golden_hi[ 9] = 16'h0927;
        golden_lo[10] = 32'hFFFF0A01; golden_mid[10] = 32'h08105020; golden_hi[10] = 16'h0A25;
        golden_lo[11] = 32'hB71D0B01; golden_mid[11] = 32'h08104030; golden_hi[11] = 16'h0B25;
        golden_lo[12] = 32'hE1C80C01; golden_mid[12] = 32'h06103020; golden_hi[12] = 16'h0C27;
        golden_lo[13] = 32'hFFFF0D01; golden_mid[13] = 32'h04102010; golden_hi[13] = 16'h0D27;
        golden_lo[14] = 32'hB71D0E01; golden_mid[14] = 32'h08104030; golden_hi[14] = 16'h0E25;
        golden_lo[15] = 32'h1E370F06; golden_mid[15] = 32'h04101027; golden_hi[15] = 16'h0F32;
        golden_lo[16] = 32'h0C730F06; golden_mid[16] = 32'h06102037; golden_hi[16] = 16'h1032;
        golden_lo[17] = 32'h21C80F06; golden_mid[17] = 32'h08103047; golden_hi[17] = 16'h1132;
        golden_lo[18] = 32'h1E370F06; golden_mid[18] = 32'h0A103067; golden_hi[18] = 16'h1232;
        golden_lo[19] = 32'h0BEE0F06; golden_mid[19] = 32'h0C104077; golden_hi[19] = 16'h1332;
        golden_lo[20] = 32'h01C80F06; golden_mid[20] = 32'h0E105087; golden_hi[20] = 16'h1432;
        golden_lo[21] = 32'h1E370F06; golden_mid[21] = 32'h101050A7; golden_hi[21] = 16'h1532;
        golden_lo[22] = 32'h08E20F06; golden_mid[22] = 32'h141070C7; golden_hi[22] = 16'h1632;
        golden_lo[23] = 32'h15AE0F06; golden_mid[23] = 32'h181080F7; golden_hi[23] = 16'h1732;
        golden_lo[24] = 32'h116A0F06; golden_mid[24] = 32'h2010B147; golden_hi[24] = 16'h1832;
        golden_lo[25] = 32'h1A160F06; golden_mid[25] = 32'h301101F7; golden_hi[25] = 16'h1932;
        golden_lo[26] = 32'h14D90F06; golden_mid[26] = 32'h40116297; golden_hi[26] = 16'h1A32;
        golden_lo[27] = 32'h15F50F06; golden_mid[27] = 32'h601213E7; golden_hi[27] = 16'h1B32;
        golden_lo[28] = 32'h16810F06; golden_mid[28] = 32'h8012C537; golden_hi[28] = 16'h1C32;
        golden_lo[29] = 32'h17510F06; golden_mid[29] = 32'h00158A77; golden_hi[29] = 16'h1D32;
        golden_lo[30] = 32'h9E370F06; golden_mid[30] = 32'h02100017; golden_hi[30] = 16'h1E32;
        golden_lo[31] = 32'hFFFF1001; golden_mid[31] = 32'h08100001; golden_hi[31] = 16'h1F45;
        golden_lo[32] = 32'hFFFF1006; golden_mid[32] = 32'h10101001; golden_hi[32] = 16'h2045;
        golden_lo[33] = 32'hFFFF1100; golden_mid[33] = 32'h20102001; golden_hi[33] = 16'h2145;
        golden_lo[34] = 32'hFFFF1100; golden_mid[34] = 32'h40103001; golden_hi[34] = 16'h2245;
        golden_lo[35] = 32'hFFFF1208; golden_mid[35] = 32'h08100006; golden_hi[35] = 16'h2345;
        golden_lo[36] = 32'hFFFF1208; golden_mid[36] = 32'h10100006; golden_hi[36] = 16'h2445;
        golden_lo[37] = 32'hFFFF1208; golden_mid[37] = 32'h20100006; golden_hi[37] = 16'h2545;
        golden_lo[38] = 32'hFFFF1208; golden_mid[38] = 32'h40100006; golden_hi[38] = 16'h2645;
        golden_lo[39] = 32'hB71D1301; golden_mid[39] = 32'h08104035; golden_hi[39] = 16'h2757;
        golden_lo[40] = 32'hE1C81301; golden_mid[40] = 32'h06103025; golden_hi[40] = 16'h2857;
        golden_lo[41] = 32'hFFFF1301; golden_mid[41] = 32'h04102015; golden_hi[41] = 16'h2957;
        golden_lo[42] = 32'h21C81401; golden_mid[42] = 32'h08103042; golden_hi[42] = 16'h2A65;
        golden_lo[43] = 32'h1E371400; golden_mid[43] = 32'h101050A2; golden_hi[43] = 16'h2B65;
        golden_lo[44] = 32'h452C1500; golden_mid[44] = 32'h20108172; golden_hi[44] = 16'h2C65;
        golden_lo[45] = 32'h452C1600; golden_mid[45] = 32'h20108172; golden_hi[45] = 16'h2D65;
        golden_lo[46] = 32'h9E371707; golden_mid[46] = 32'h04100033; golden_hi[46] = 16'h2E77;
        golden_lo[47] = 32'h9E371707; golden_mid[47] = 32'h08100073; golden_hi[47] = 16'h2F77;
        golden_lo[48] = 32'h9E371700; golden_mid[48] = 32'h101000F3; golden_hi[48] = 16'h3077;
        golden_lo[49] = 32'h9E371700; golden_mid[49] = 32'h201001F3; golden_hi[49] = 16'h3177;
        golden_lo[50] = 32'h9E371700; golden_mid[50] = 32'h401003F3; golden_hi[50] = 16'h3277;
        golden_lo[51] = 32'h9E371800; golden_mid[51] = 32'h04000043; golden_hi[51] = 16'h3377;
        golden_lo[52] = 32'h9E371800; golden_mid[52] = 32'h101000F3; golden_hi[52] = 16'h3477;
        golden_lo[53] = 32'h9E371901; golden_mid[53] = 32'h08000084; golden_hi[53] = 16'h3577;
        golden_lo[54] = 32'h452C1A00; golden_mid[54] = 32'h20108178; golden_hi[54] = 16'h3686;
        golden_lo[55] = 32'h78FA1A00; golden_mid[55] = 32'h40108378; golden_hi[55] = 16'h3786;
        golden_lo[56] = 32'h538C1B00; golden_mid[56] = 32'h20107188; golden_hi[56] = 16'h3886;
        golden_lo[57] = 32'h7E371B00; golden_mid[57] = 32'h40107388; golden_hi[57] = 16'h3986;
        golden_lo[58] = 32'h4E371C00; golden_mid[58] = 32'h4010F308; golden_hi[58] = 16'h3A86;
        golden_lo[59] = 32'h452C1D00; golden_mid[59] = 32'h20108178; golden_hi[59] = 16'h3B86;
        golden_lo[60] = 32'h78FA1D00; golden_mid[60] = 32'h40108378; golden_hi[60] = 16'h3C86;
        golden_lo[61] = 32'h452C1E00; golden_mid[61] = 32'h20108178; golden_hi[61] = 16'h3D86;
        golden_lo[62] = 32'h62371F00; golden_mid[62] = 32'h5010F408; golden_hi[62] = 16'h3E86;
        golden_lo[63] = 32'h69B42000; golden_mid[63] = 32'h30108278; golden_hi[63] = 16'h3F86;
        golden_lo[64] = 32'hFFFF2100; golden_mid[64] = 32'h20100009; golden_hi[64] = 16'h4097;
        golden_lo[65] = 32'hFFFF2200; golden_mid[65] = 32'h20100009; golden_hi[65] = 16'h4197;
        golden_lo[66] = 32'h452C2300; golden_mid[66] = 32'h20108179; golden_hi[66] = 16'h4292;
        golden_lo[67] = 32'h452C2400; golden_mid[67] = 32'h20108179; golden_hi[67] = 16'h4392;
        golden_lo[68] = 32'h1E372500; golden_mid[68] = 32'h101050A0; golden_hi[68] = 16'h44A7;
        golden_lo[69] = 32'hB71D2601; golden_mid[69] = 32'h08104030; golden_hi[69] = 16'h45A5;
        golden_lo[70] = 32'h9E372701; golden_mid[70] = 32'h04000043; golden_hi[70] = 16'h46A5;
        golden_lo[71] = 32'h9E372807; golden_mid[71] = 32'h02100013; golden_hi[71] = 16'h47A5;
        golden_lo[72] = 32'h7BEE2900; golden_mid[72] = 32'h8010F700; golden_hi[72] = 16'h48B7;
        golden_lo[73] = 32'hFFFF2A00; golden_mid[73] = 32'h80107001; golden_hi[73] = 16'h49B5;
        golden_lo[74] = 32'h83232B00; golden_mid[74] = 32'h8010B680; golden_hi[74] = 16'h4AB1;
        golden_lo[75] = 32'h9E372C01; golden_mid[75] = 32'h04000043; golden_hi[75] = 16'h4BC5;
        golden_lo[76] = 32'h9E372D00; golden_mid[76] = 32'h04000043; golden_hi[76] = 16'h4CC5;
        golden_lo[77] = 32'h0C730C01; golden_mid[77] = 32'h06102030; golden_hi[77] = 16'h4D27;
        golden_lo[78] = 32'hFFFF1301; golden_mid[78] = 32'h08008005; golden_hi[78] = 16'h4E57;
        golden_lo[79] = 32'h9E371301; golden_mid[79] = 32'h08100075; golden_hi[79] = 16'h4F57;
    end

    reg [7:0] exp_byte;

    task rom_check_full(input [6:0] addr, input integer idx);
    begin
        pre_err = errors;
        ui_in = {1'b0, addr};
        @(posedge clk); #1;
        ui_in = 8'h00;
        @(posedge clk); #1;
        ui_in = 8'h80;

        for (b = 0; b < 10; b = b + 1) begin
            case (b)
                0: exp_byte = golden_lo[idx][7:0];
                1: exp_byte = golden_lo[idx][15:8];
                2: exp_byte = golden_lo[idx][23:16];
                3: exp_byte = golden_lo[idx][31:24];
                4: exp_byte = golden_mid[idx][7:0];
                5: exp_byte = golden_mid[idx][15:8];
                6: exp_byte = golden_mid[idx][23:16];
                7: exp_byte = golden_mid[idx][31:24];
                8: exp_byte = golden_hi[idx][7:0];
                9: exp_byte = golden_hi[idx][15:8];
            endcase
            if (uo_out !== exp_byte) begin
                $display("FAIL: rom[%0d] byte%0d got=%02X exp=%02X", idx, b, uo_out, exp_byte);
                errors = errors + 1;
            end
            if (b < 9) begin @(posedge clk); #1; end
        end
        if (errors == pre_err) $display("PASS: rom[%0d]", idx);
        @(posedge clk); #1;
        @(posedge clk); #1;
    end
    endtask

    reg [6:0] addr_val;

    initial begin
        #100;
        rst_n = 1;
        @(posedge clk); #1;

        for (i = 0; i < 80; i = i + 1) begin
            addr_val = i[6:0];
            rom_check_full(addr_val, i);
        end

        @(posedge clk);
        if (errors == 0)
            $display("ROM GOLDEN: ALL 80 RECORDS PASS (800 bytes verified)");
        else
            $display("ROM GOLDEN: %0d FAILURES", errors);
        $finish;
    end

    initial begin
        $dumpfile("tb_rom_golden.vcd");
        $dumpvars(0, tb_rom_golden);
    end
endmodule
