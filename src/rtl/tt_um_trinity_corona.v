// SPDX-License-Identifier: Apache-2.0
// tt-trinity-corona / src/rtl/tt_um_trinity_corona.v
// Top module: anchor probe + ROM skeleton + MVP Tier-1 dispatch.
// Protocol v2: two-byte CMD (fmt_id + byte_count), then raw 8-bit data,
// then auto-transition to STATUS readback.

`default_nettype none

module tt_um_trinity_corona (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // =====================================================================
    // Protocol v2 states
    // =====================================================================
    localparam [2:0] ST_IDLE    = 3'd0;
    localparam [2:0] ST_CMD2    = 3'd1;  // waiting for byte_count
    localparam [2:0] ST_DATA    = 3'd2;  // accepting raw 8-bit data
    localparam [2:0] ST_STATUS  = 3'd3;  // streaming result bytes
    localparam [2:0] ST_DONE    = 3'd4;  // readback complete, return to idle

    localparam [6:0] FMT_ID_ANCHOR = 7'h7F;
    localparam [7:0] ANCHOR_UO     = 8'hC0;
    localparam [7:0] ANCHOR_UIO    = 8'h47;
    localparam [7:0] NOT_IMPL      = 8'hFF;

    // fmt_id assignments (aligned with ROM catalog / SSOT ordering)
    localparam [6:0] FMT_BF16          = 7'd8;    // cluster 2: ML low-precision
    localparam [6:0] FMT_POSIT8        = 7'd31;   // cluster 4: posit/unum III
    localparam [6:0] FMT_MXFP8_E4M3   = 7'd39;   // cluster 5: OCP MX
    localparam [6:0] FMT_FP6_E3M2      = 7'd40;   // cluster 5: OCP MX
    localparam [6:0] FMT_FP4           = 7'd41;   // cluster 5: OCP MX
    localparam [6:0] FMT_LNS8          = 7'd42;   // cluster 6: LNS
    localparam [6:0] FMT_BCD           = 7'd53;   // cluster 7: integer/fixed
    localparam [6:0] FMT_TF32          = 7'd9;    // cluster 2: ML low-precision
    localparam [6:0] FMT_FP8_E5M2     = 7'd10;   // cluster 2: ML low-precision
    localparam [6:0] FMT_NF4           = 7'd70;   // cluster 10: compression
    localparam [6:0] FMT_INT8          = 7'd47;   // cluster 7: integer/fixed
    localparam [6:0] FMT_FP6_E2M3     = 7'd77;   // cluster 2: Blackwell sub-8-bit
    localparam [6:0] FMT_E8M0         = 7'd78;   // cluster 5: OCP MX shared scale
    localparam [6:0] FMT_MXINT8       = 7'd79;   // cluster 5: OCP MX integer

    // =====================================================================
    // Anchor probe (combinational, always active)
    // =====================================================================
    wire is_anchor_cmd = (ui_in[7] == 1'b0) && (ui_in[6:0] == FMT_ID_ANCHOR);

    // =====================================================================
    // Protocol v2 state machine
    //
    // IDLE: ui_in[7]=0 -> CMD1 (fmt_id = ui_in[6:0])
    //       ui_in[7]=1 -> ignored (stay idle)
    // CMD2: ui_in[3:0] = byte_count (1-4 valid, 0 = ROM readback)
    // DATA: accept exactly byte_count raw 8-bit bytes (no mode inspection)
    // STATUS: stream 4 result bytes on uo_out, one per clock
    // DONE: one-cycle gap, then back to IDLE
    // =====================================================================
    reg [2:0]  state;
    reg [6:0]  fmt_id_r;
    reg [3:0]  data_cnt;     // counts down remaining data bytes
    reg [3:0]  status_cnt;   // counts up during readback (0-9 for ROM, 0-3 for decode)
    reg        rom_mode;     // 1 = ROM readback (byte_count was 0), 0 = decode
    reg [31:0] data_in_buf;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= ST_IDLE;
            fmt_id_r    <= 7'd0;
            data_cnt    <= 4'd0;
            status_cnt  <= 4'd0;
            rom_mode    <= 1'b0;
            data_in_buf <= 32'd0;
        end else if (ena) begin
            case (state)
                ST_IDLE: begin
                    status_cnt <= 4'd0;
                    rom_mode   <= 1'b0;
                    if (ui_in[7] == 1'b0 && !is_anchor_cmd) begin
                        fmt_id_r    <= ui_in[6:0];
                        data_in_buf <= 32'd0;
                        state       <= ST_CMD2;
                    end
                end

                ST_CMD2: begin
                    data_cnt <= ui_in[3:0];
                    if (ui_in[3:0] == 4'd0) begin
                        rom_mode <= 1'b1;    // ROM readback mode
                        state    <= ST_STATUS;
                    end else begin
                        rom_mode <= 1'b0;
                        state    <= ST_DATA;
                    end
                end

                ST_DATA: begin
                    // Raw 8-bit data: ALL 256 byte values accepted
                    data_in_buf <= {ui_in, data_in_buf[31:8]};
                    if (data_cnt == 4'd1) begin
                        state      <= ST_STATUS;
                        status_cnt <= 4'd0;
                    end
                    data_cnt <= data_cnt - 4'd1;
                end

                ST_STATUS: begin
                    // ROM mode: stream 10 bytes; decode mode: stream 4 bytes
                    if (rom_mode) begin
                        if (status_cnt == 4'd9)
                            state <= ST_DONE;
                    end else begin
                        if (status_cnt == 4'd3)
                            state <= ST_DONE;
                    end
                    status_cnt <= status_cnt + 4'd1;
                end

                ST_DONE: begin
                    state <= ST_IDLE;
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

    // =====================================================================
    // Tier-1 decoder instances
    // =====================================================================

    // Decoder bit positions: right-shift register {ui_in, data_in_buf[31:8]}
    // puts data at MSB side. After N bytes: data at [31 : 32-8*N].
    // 1-byte formats: [31:24]; 2-byte: [31:16]; 3-byte: [26:8] for 19-bit TF32.

    wire [31:0] bf16_fp32;
    wire        bf16_zero, bf16_inf, bf16_nan;
    bf16_decode u_bf16 (
        .bf16_in(data_in_buf[31:16]), .fp32_out(bf16_fp32),
        .is_zero(bf16_zero), .is_inf(bf16_inf), .is_nan(bf16_nan)
    );

    wire [31:0] mxfp8_fp32;
    wire        mxfp8_zero, mxfp8_nan;
    mxfp8_e4m3_decode u_mxfp8 (
        .e4m3_in(data_in_buf[31:24]), .fp32_out(mxfp8_fp32),
        .is_zero(mxfp8_zero), .is_nan(mxfp8_nan)
    );

    wire [6:0] bcd_bin;
    wire       bcd_valid;
    bcd_decode u_bcd (
        .bcd_in(data_in_buf[31:24]), .bin_out(bcd_bin), .valid(bcd_valid)
    );

    wire        lns8_sign;
    wire [15:0] lns8_mag;
    wire        lns8_zero;
    lns8_decode u_lns8 (
        .lns_in(data_in_buf[31:24]), .sign_out(lns8_sign),
        .magnitude(lns8_mag), .is_zero(lns8_zero)
    );

    wire [31:0] posit8_fp32;
    wire        posit8_zero, posit8_nar;
    posit8_decode u_posit8 (
        .posit_in(data_in_buf[31:24]), .fp32_out(posit8_fp32),
        .is_zero(posit8_zero), .is_nar(posit8_nar)
    );

    wire [31:0] fp4_fp32;
    fp4_decode u_fp4 (
        .fp4_in(data_in_buf[27:24]), .fp32_out(fp4_fp32)
    );

    wire [31:0] fp6_fp32;
    fp6_e3m2_decode u_fp6 (
        .fp6_in(data_in_buf[29:24]), .fp32_out(fp6_fp32)
    );

    wire [31:0] nf4_fp32;
    nf4_decode u_nf4 (
        .nf4_in(data_in_buf[27:24]), .fp32_out(nf4_fp32)
    );

    wire [31:0] tf32_fp32;
    wire        tf32_zero, tf32_inf, tf32_nan;
    tf32_decode u_tf32 (
        .tf32_in(data_in_buf[26:8]), .fp32_out(tf32_fp32),
        .is_zero(tf32_zero), .is_inf(tf32_inf), .is_nan(tf32_nan)
    );

    wire [31:0] fp8e5m2_fp32;
    wire        fp8e5m2_zero, fp8e5m2_inf, fp8e5m2_nan;
    fp8_e5m2_decode u_fp8e5m2 (
        .e5m2_in(data_in_buf[31:24]), .fp32_out(fp8e5m2_fp32),
        .is_zero(fp8e5m2_zero), .is_inf(fp8e5m2_inf), .is_nan(fp8e5m2_nan)
    );

    wire [31:0] fp6e2m3_fp32;
    wire        fp6e2m3_zero;
    fp6_e2m3_decode u_fp6e2m3 (
        .fp6_in(data_in_buf[29:24]), .fp32_out(fp6e2m3_fp32),
        .is_zero(fp6e2m3_zero)
    );

    wire [31:0] int8_i32;
    wire        int8_zero;
    int8_decode u_int8 (
        .int8_in(data_in_buf[31:24]), .int32_out(int8_i32),
        .is_zero(int8_zero)
    );

    wire [31:0] e8m0_fp32;
    wire        e8m0_nan;
    e8m0_decode u_e8m0 (
        .e8m0_in(data_in_buf[31:24]), .fp32_out(e8m0_fp32),
        .is_nan(e8m0_nan)
    );

    wire [31:0] mxint8_fp32;
    wire        mxint8_zero, mxint8_reserved;
    mxint8_decode u_mxint8 (
        .mxint8_in(data_in_buf[31:24]), .fp32_out(mxint8_fp32),
        .is_zero(mxint8_zero), .is_reserved(mxint8_reserved)
    );

    // =====================================================================
    // ROM instance (placeholder -- Phase B populates)
    // =====================================================================
    wire [79:0] rom_data;
    format_rom u_rom (
        .clk(clk), .addr(fmt_id_r), .data(rom_data)
    );

    // =====================================================================
    // Decoder output mux
    // =====================================================================
    reg [31:0] decode_result;
    reg        has_decoder;

    always @(*) begin
        decode_result = 32'd0;
        has_decoder   = 1'b0;
        case (fmt_id_r)
            FMT_BF16:        begin decode_result = bf16_fp32;   has_decoder = 1'b1; end
            FMT_MXFP8_E4M3: begin decode_result = mxfp8_fp32;  has_decoder = 1'b1; end
            FMT_LNS8:        begin decode_result = {lns8_sign, 15'b0, lns8_mag}; has_decoder = 1'b1; end
            FMT_BCD:         begin decode_result = {25'b0, bcd_bin}; has_decoder = 1'b1; end
            FMT_POSIT8:      begin decode_result = posit8_fp32; has_decoder = 1'b1; end
            FMT_FP4:         begin decode_result = fp4_fp32;    has_decoder = 1'b1; end
            FMT_FP6_E3M2:    begin decode_result = fp6_fp32;    has_decoder = 1'b1; end
            FMT_NF4:         begin decode_result = nf4_fp32;    has_decoder = 1'b1; end
            FMT_TF32:        begin decode_result = tf32_fp32;   has_decoder = 1'b1; end
            FMT_FP8_E5M2:   begin decode_result = fp8e5m2_fp32; has_decoder = 1'b1; end
            FMT_FP6_E2M3:   begin decode_result = fp6e2m3_fp32; has_decoder = 1'b1; end
            FMT_INT8:        begin decode_result = int8_i32;    has_decoder = 1'b1; end
            FMT_E8M0:        begin decode_result = e8m0_fp32;   has_decoder = 1'b1; end
            FMT_MXINT8:      begin decode_result = mxint8_fp32; has_decoder = 1'b1; end
            default:         begin decode_result = 32'd0;       has_decoder = 1'b0; end
        endcase
    end

    // Select output byte based on status_cnt during STATUS readback
    reg [7:0] status_byte;
    always @(*) begin
        if (rom_mode) begin
            // ROM readback: 10 bytes from rom_data[79:0], LSB first
            case (status_cnt)
                4'd0: status_byte = rom_data[7:0];
                4'd1: status_byte = rom_data[15:8];
                4'd2: status_byte = rom_data[23:16];
                4'd3: status_byte = rom_data[31:24];
                4'd4: status_byte = rom_data[39:32];
                4'd5: status_byte = rom_data[47:40];
                4'd6: status_byte = rom_data[55:48];
                4'd7: status_byte = rom_data[63:56];
                4'd8: status_byte = rom_data[71:64];
                4'd9: status_byte = rom_data[79:72];
                default: status_byte = 8'h00;
            endcase
        end else if (!has_decoder) begin
            case (status_cnt[1:0])
                2'd0: status_byte = NOT_IMPL;
                2'd1: status_byte = {1'b0, fmt_id_r};
                2'd2: status_byte = 8'h07;          // status_id = SPEC
                2'd3: status_byte = 8'h4E;          // 'N' = Not-implemented
            endcase
        end else begin
            case (status_cnt[1:0])
                2'd0: status_byte = decode_result[7:0];
                2'd1: status_byte = decode_result[15:8];
                2'd2: status_byte = decode_result[23:16];
                2'd3: status_byte = decode_result[31:24];
            endcase
        end
    end

    // =====================================================================
    // Output mux
    // =====================================================================
    reg [7:0] uo_out_r;
    reg [7:0] uio_out_r;

    always @(*) begin
        if (state == ST_STATUS) begin
            uo_out_r  = status_byte;
            uio_out_r = 8'h00;
        end else if (is_anchor_cmd) begin
            uo_out_r  = ANCHOR_UO;
            uio_out_r = ANCHOR_UIO;
        end else begin
            uo_out_r  = 8'h00;
            uio_out_r = 8'h00;
        end
    end

    assign uo_out  = uo_out_r;
    assign uio_out = uio_out_r;
    assign uio_oe  = is_anchor_cmd ? 8'hFF : 8'h00;

    wire _unused = &{uio_in, bcd_valid, bf16_zero, bf16_inf, bf16_nan,
                     mxfp8_zero, mxfp8_nan, lns8_zero, posit8_zero, posit8_nar,
                     tf32_zero, tf32_inf, tf32_nan,
                     fp8e5m2_zero, fp8e5m2_inf, fp8e5m2_nan,
                     fp6e2m3_zero, int8_zero,
                     e8m0_nan, mxint8_zero, mxint8_reserved,
                     1'b0};

endmodule
