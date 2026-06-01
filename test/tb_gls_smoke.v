// Gate-level simulation smoke test (no cocotb dependency).
// Tests all 18 Tier-1 decoders + ROM readback + NOT_IMPL sentinel + reset recovery.
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

    integer pre_err;
    task decode_1byte(
        input [6:0] fmt_id,
        input [7:0] data_byte,
        input [31:0] expected_fp32,
        input [159:0] name
    );
    begin
        pre_err = errors;
        ui_in = {1'b0, fmt_id};
        @(posedge clk); #1;
        ui_in = 8'h01;
        @(posedge clk); #1;
        ui_in = data_byte;
        @(posedge clk); #1;
        ui_in = 8'h80;
        check(expected_fp32[7:0],   8'h00, name);
        @(posedge clk); #1;
        check(expected_fp32[15:8],  8'h00, name);
        @(posedge clk); #1;
        check(expected_fp32[23:16], 8'h00, name);
        @(posedge clk); #1;
        check(expected_fp32[31:24], 8'h00, name);
        if (errors == pre_err) $display("PASS: %0s -> %08X", name, expected_fp32);
        @(posedge clk); #1;
        @(posedge clk); #1;
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

        // DONE→IDLE: FSM needs 2 cycles (STATUS→DONE→IDLE)
        @(posedge clk); #1;
        @(posedge clk); #1;

        // --- Test 3: Posit8 decode of +1.0 (0x40 -> 0x3F800000) ---
        decode_1byte(7'd31, 8'h40, 32'h3F800000, "posit8 +1.0");

        // --- Test 4: FP4 E2M1 decode of +1.0 (0x02 -> 0x3F800000) ---
        decode_1byte(7'd41, 8'h02, 32'h3F800000, "fp4 +1.0");

        // --- Test 5: NF4 decode of +1.0 (0x0F -> 0x3F800000) ---
        decode_1byte(7'd70, 8'h0F, 32'h3F800000, "nf4 +1.0");

        // --- Test 6: BitNet decode of +1 (0x01 -> 0x3F800000) ---
        decode_1byte(7'd71, 8'h01, 32'h3F800000, "bitnet +1");

        // --- Test 7: INT4 decode of +1 (0x01 -> 0x00000001) ---
        decode_1byte(7'd46, 8'h01, 32'h00000001, "int4 +1");

        // --- Test 8: FP8 E5M2 decode of +1.0 (0x3C -> 0x3F800000) ---
        decode_1byte(7'd10, 8'h3C, 32'h3F800000, "fp8e5m2 +1.0");

        // --- Test 9: E8M0 decode of 2^0 (0x7F -> 0x3F800000) ---
        decode_1byte(7'd78, 8'h7F, 32'h3F800000, "e8m0 2^0");

        // --- Test 10: MXINT8 decode of +1.0 (0x40 -> 0x3F800000) ---
        decode_1byte(7'd79, 8'h40, 32'h3F800000, "mxint8 +1.0");

        // --- Test 11: TF32 decode of +1.0 (3 bytes -> 0x3F800000) ---
        pre_err = errors;
        ui_in = 8'h09;
        @(posedge clk); #1;
        ui_in = 8'h03;
        @(posedge clk); #1;
        ui_in = 8'h00;
        @(posedge clk); #1;
        ui_in = 8'hFC;
        @(posedge clk); #1;
        ui_in = 8'h01;
        @(posedge clk); #1;
        ui_in = 8'h80;
        check(8'h00, 8'h00, "tf32 status[0]");
        @(posedge clk); #1;
        check(8'h00, 8'h00, "tf32 status[1]");
        @(posedge clk); #1;
        check(8'h80, 8'h00, "tf32 status[2]");
        @(posedge clk); #1;
        check(8'h3F, 8'h00, "tf32 status[3]");
        if (errors == pre_err) $display("PASS: tf32 +1.0 -> 3F800000");
        @(posedge clk); #1;
        @(posedge clk); #1;

        // --- Test 12: FP6 E3M2 decode of +1.0 (0x0C -> 0x3F800000) ---
        decode_1byte(7'd40, 8'h0C, 32'h3F800000, "fp6e3m2 +1.0");

        // --- Test 13: FP6 E2M3 decode of +1.0 (0x08 -> 0x3F800000) ---
        decode_1byte(7'd77, 8'h08, 32'h3F800000, "fp6e2m3 +1.0");

        // --- Test 14: MXFP8 E4M3 decode of +1.0 (0x38 -> 0x3F800000) ---
        decode_1byte(7'd39, 8'h38, 32'h3F800000, "mxfp8 +1.0");

        // --- Test 15: FP8 E4M3 FNUZ decode of +1.0 (0x40 -> 0x3F800000) ---
        decode_1byte(7'd14, 8'h40, 32'h3F800000, "fnuz +1.0");

        // --- Test 16: INT8 decode of +1 (0x01 -> 0x00000001) ---
        decode_1byte(7'd47, 8'h01, 32'h00000001, "int8 +1");

        // --- Test 17: BCD decode of 42 (0x42 -> 0x0000002A) ---
        decode_1byte(7'd53, 8'h42, 32'h0000002A, "bcd 42");

        // --- Test 18: LNS8 decode of 0x01 (magnitude=267=0x010B) ---
        decode_1byte(7'd42, 8'h01, 32'h0000010B, "lns8 0x01");

        // --- Test 19: NOT_IMPL sentinel (fmt_id=1, unsupported) ---
        decode_1byte(7'd1, 8'hAA, 32'h4E0701FF, "not-impl");

        // --- Test 20: ROM readback for fmt_id=8 (BF16) ---
        ui_in = 8'h08;
        @(posedge clk); #1;
        ui_in = 8'h00;
        @(posedge clk); #1;
        ui_in = 8'h80;
        if (uo_out === 8'h00 && uio_out === 8'h00) begin
            $display("FAIL: ROM readback byte[0] all zeros");
            errors = errors + 1;
        end else begin
            $display("PASS: ROM readback byte[0] = %02X", uo_out);
        end
        repeat(11) begin @(posedge clk); #1; end

        // --- Test 21: Reset re-entry (FSM recovery) ---
        ui_in = 8'h08;  // CMD1: BF16
        @(posedge clk); #1;
        rst_n = 0;       // Assert reset mid-CMD2
        @(posedge clk); @(posedge clk); #1;
        rst_n = 1;       // Release reset
        @(posedge clk); #1;
        // Verify FSM recovered: anchor probe should work
        ui_in = 8'h7F;
        #2;
        if (uo_out !== 8'hC0 || uio_out !== 8'h47) begin
            $display("FAIL: reset-recovery anchor uo=%02X uio=%02X", uo_out, uio_out);
            errors = errors + 1;
        end else begin
            $display("PASS: reset-recovery anchor = 0x47C0");
        end

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
