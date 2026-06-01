// Gate-level simulation smoke test (no cocotb dependency).
// Tests anchor probe + one BF16 decode against the synthesized netlist.
// Usage: yosys -> synth_netlist.v, then iverilog + simcells.v + this file.
`timescale 1ns/1ps

module tb_gls_smoke;
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

    task check(input [7:0] expected_uo, input [7:0] expected_uio, input [159:0] label);
    begin
        if (uo_out !== expected_uo || uio_out !== expected_uio) begin
            $display("FAIL [%0s]: uo=%02X uio=%02X (expected %02X %02X)",
                     label, uo_out, uio_out, expected_uo, expected_uio);
            errors = errors + 1;
        end
    end
    endtask

    initial begin
        // Reset
        #100;
        rst_n = 1;
        @(posedge clk); #1;

        // --- Test 1: Anchor probe (combinational) ---
        ui_in = 8'h7F;
        #2;
        if (uo_out !== 8'hC0 || uio_out !== 8'h47 || uio_oe !== 8'hFF) begin
            $display("FAIL: anchor uo=%02X uio=%02X oe=%02X", uo_out, uio_out, uio_oe);
            errors = errors + 1;
        end else begin
            $display("PASS: anchor = 0x47C0, oe=FF");
        end

        // --- Test 2: BF16 decode of +1.0 (0x3F80) ---
        // CMD1: fmt_id = 8 (BF16)
        ui_in = 8'h08;
        @(posedge clk); #1;
        // CMD2: byte_count = 2
        ui_in = 8'h02;
        @(posedge clk); #1;
        // DATA byte 0 (LSB): 0x80
        ui_in = 8'h80;
        @(posedge clk); #1;
        // DATA byte 1 (MSB): 0x3F — on this edge, FSM enters STATUS
        ui_in = 8'h3F;
        @(posedge clk); #1;
        // STATUS: FSM is now in STATUS, status_cnt=0 visible after this edge
        ui_in = 8'h80;
        // status_cnt advances each posedge; sample byte N after edge N+1
        // Byte 0 (cnt=0): visible NOW (state just entered STATUS)
        check(8'h00, 8'h00, "bf16 status[0]");
        @(posedge clk); #1;
        check(8'h00, 8'h00, "bf16 status[1]");
        @(posedge clk); #1;
        check(8'h80, 8'h00, "bf16 status[2]");
        @(posedge clk); #1;
        check(8'h3F, 8'h00, "bf16 status[3]");

        // DONE cycle
        @(posedge clk); #1;

        // --- Summary ---
        @(posedge clk);
        if (errors == 0)
            $display("GLS SMOKE: ALL PASS");
        else
            $display("GLS SMOKE: %0d FAILURES", errors);
        $finish;
    end

    initial begin
        $dumpfile("tb_gls_smoke.vcd");
        $dumpvars(0, tb_gls_smoke);
    end
endmodule
