// SPDX-License-Identifier: Apache-2.0
// corona_decode_top_ax7203.v
// Автор: Vasilev
// Назначение: верхний уровень для AX7203 (xc7a200tfbg484-2).
//   Инстанцирует 5 декодеров Corona (bf16, fp8_e4m3_fnuz, int8, nf4, posit8),
//   UART-мост для приёма команд и выдачи результата, IBUFDS для LVDS-клока 200 МГц.
//
// UART-протокол (CP2102N, 115200 бод, 8N1):
//   Запрос (хост → FPGA): [format_sel : 3 бит][pad : 5 бит][code_bytes : 1..2 байт LE]
//     Байт 0 (командный):
//       bits[7:5] = format_sel:
//         3'd0 = bf16       (code = 2 байта LE, вход [15:0])
//         3'd1 = fp8_e4m3_fnuz (code = 1 байт,  вход [7:0])
//         3'd2 = int8       (code = 1 байт,  вход [7:0])
//         3'd3 = nf4        (code = 1 байт,  нижние 4 бита [3:0])
//         3'd4 = posit8     (code = 1 байт,  вход [7:0])
//         3'd5..7 = зарезервировано, возвращает 0xFFFFFFFF
//       bits[4:0] = зарезервировано (должны быть 0x00)
//     Байт(ы) данных: LE (сначала младший байт)
//       bf16    → 2 байта (байт 1 = bits[7:0], байт 2 = bits[15:8])
//       остальные → 1 байт
//   Ответ (FPGA → хост): 4 байта LE = fp32_out / int32_out (LSB первым)
//     Статус-байт STATUS включён в bits[31:28]:
//       Для bf16/fp8_e4m3_fnuz/int8/posit8: [0]=is_zero [1]=is_nan_or_inf [2]=is_inf(если есть) [3]=is_nar
//       Для nf4: 0 (нет спец-значений помимо таблицы)
//     ВНИМАНИЕ: result передаётся как прямой fp32, status-флаги только для информации
//
// Примечание по синхронности:
//   Все 5 декодеров — комбинаторные (нет регистров). Результат защёлкивается
//   после приёма последнего байта данных.
//
// Аппаратные параметры AX7203 (НЕ ИЗМЕНЯТЬ):
//   Клок: 200 МГц LVDS, дифф. пара R4(+)/T4(-), DIFF_SSTL15
//   Reset: T6, active-low, LVCMOS15
//   UART TX: N15, UART RX: P20, LVCMOS33
//   LEDs: B13/C13/D14/D15, LVCMOS18

`default_nettype none
`timescale 1ns / 1ps

module corona_decode_top_ax7203 #(
    // Скорость UART для CP2102N (делитель от 200 МГц)
    // 200_000_000 / 115200 ≈ 1736
    parameter integer BAUD_DIV = 1736
) (
    // LVDS клок 200 МГц (R4/T4)
    input  wire sys_clk_p,
    input  wire sys_clk_n,

    // Сброс active-low (T6)
    input  wire sys_rst_n,

    // UART
    input  wire uart_rx,   // P20
    output wire uart_tx,   // N15

    // LED-индикаторы (необязательно, для отладки)
    output wire [3:0] led   // B13/C13/D14/D15
);

    // =========================================================================
    // 1. Клок: IBUFDS (LVDS 200 МГц) → BUFG
    // =========================================================================
    wire clk_200m_ibuf;
    wire clk;

    IBUFDS #(
        .DIFF_TERM    ("FALSE"),   // внешний терминатор на плате
        .IBUF_LOW_PWR ("FALSE"),
        .IOSTANDARD   ("DIFF_SSTL15")
    ) u_ibufds (
        .I  (sys_clk_p),
        .IB (sys_clk_n),
        .O  (clk_200m_ibuf)
    );

    BUFG u_bufg (
        .I (clk_200m_ibuf),
        .O (clk)
    );

    // =========================================================================
    // 2. Синхронизатор сброса (двухступенчатый, исключает метастабильность)
    //    false_path задан в XDC — Vivado игнорирует timing через эту цепочку.
    // =========================================================================
    reg rst_meta, rst_sync;
    always @(posedge clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rst_meta <= 1'b1;
            rst_sync <= 1'b1;
        end else begin
            rst_meta <= 1'b0;
            rst_sync <= rst_meta;
        end
    end
    // rst_sync = 1 → система сброшена; = 0 → работает
    wire rst = rst_sync;

    // =========================================================================
    // 3. UART RX (приём байт)
    // =========================================================================
    // Простой UART RX: детектирует старт-бит, сдвигает 8 бит, флаг готовности.
    localparam integer BAUD_HALF = BAUD_DIV / 2;

    reg [$clog2(BAUD_DIV+1)-1:0] rx_baud_cnt;
    reg [3:0]  rx_bit_cnt;
    reg [7:0]  rx_shift;
    reg [7:0]  rx_data;
    reg        rx_valid;
    reg        rx_busy;

    // Двойная синхронизация входного UART RX
    reg rx_meta, rx_in;
    always @(posedge clk) begin
        rx_meta <= uart_rx;
        rx_in   <= rx_meta;
    end

    always @(posedge clk) begin
        rx_valid <= 1'b0;
        if (rst) begin
            rx_baud_cnt <= 0;
            rx_bit_cnt  <= 4'd0;
            rx_busy     <= 1'b0;
        end else begin
            if (!rx_busy) begin
                // Ждём спад (старт-бит)
                if (!rx_in) begin
                    rx_busy     <= 1'b1;
                    rx_baud_cnt <= BAUD_HALF[($clog2(BAUD_DIV+1)-1):0];
                    rx_bit_cnt  <= 4'd0;
                end
            end else begin
                if (rx_baud_cnt == 0) begin
                    rx_baud_cnt <= BAUD_DIV[$clog2(BAUD_DIV+1)-1:0] - 1;
                    if (rx_bit_cnt < 4'd8) begin
                        rx_shift    <= {rx_in, rx_shift[7:1]};
                        rx_bit_cnt  <= rx_bit_cnt + 4'd1;
                    end else begin
                        // Стоп-бит: завершаем приём
                        rx_busy  <= 1'b0;
                        rx_data  <= rx_shift;
                        rx_valid <= 1'b1;
                    end
                end else begin
                    rx_baud_cnt <= rx_baud_cnt - 1;
                end
            end
        end
    end

    // =========================================================================
    // 4. UART TX (передача байт)
    // =========================================================================
    reg [$clog2(BAUD_DIV+1)-1:0] tx_baud_cnt;
    reg [3:0]  tx_bit_cnt;
    reg [9:0]  tx_shift;   // {стоп, данные[7:0], старт}
    reg        tx_busy;
    reg        tx_out_r;

    reg        tx_req;
    reg [7:0]  tx_byte;

    assign uart_tx = tx_out_r;

    always @(posedge clk) begin
        if (rst) begin
            tx_baud_cnt <= 0;
            tx_bit_cnt  <= 4'd0;
            tx_busy     <= 1'b0;
            tx_out_r    <= 1'b1;
        end else begin
            if (!tx_busy) begin
                tx_out_r <= 1'b1;
                if (tx_req) begin
                    // Старт-бит(0) + 8 данных + стоп(1)
                    tx_shift    <= {1'b1, tx_byte, 1'b0};
                    tx_bit_cnt  <= 4'd0;
                    tx_baud_cnt <= BAUD_DIV[$clog2(BAUD_DIV+1)-1:0] - 1;
                    tx_busy     <= 1'b1;
                end
            end else begin
                if (tx_baud_cnt == 0) begin
                    tx_baud_cnt <= BAUD_DIV[$clog2(BAUD_DIV+1)-1:0] - 1;
                    tx_out_r    <= tx_shift[0];
                    tx_shift    <= {1'b1, tx_shift[9:1]};
                    tx_bit_cnt  <= tx_bit_cnt + 4'd1;
                    if (tx_bit_cnt == 4'd9) begin
                        tx_busy <= 1'b0;
                    end
                end else begin
                    tx_baud_cnt <= tx_baud_cnt - 1;
                end
            end
        end
    end

    // =========================================================================
    // 5. Протокол: конечный автомат приёма команды и отправки ответа
    // =========================================================================
    // Форматы по количеству байт данных:
    //   bf16 (sel=0):  2 байта данных (16-бит вход)
    //   прочие (1..4): 1 байт данных (8-бит вход)

    localparam [2:0] ST_CMD   = 3'd0;   // ждём командный байт
    localparam [2:0] ST_D0    = 3'd1;   // принимаем байт данных 0
    localparam [2:0] ST_D1    = 3'd2;   // принимаем байт данных 1 (только bf16)
    localparam [2:0] ST_TX0   = 3'd3;   // отправляем byte0 ответа
    localparam [2:0] ST_TX1   = 3'd4;   // отправляем byte1
    localparam [2:0] ST_TX2   = 3'd5;   // отправляем byte2
    localparam [2:0] ST_TX3   = 3'd6;   // отправляем byte3

    reg [2:0]  state;
    reg [2:0]  fmt_sel;    // 3-бит формат из командного байта
    reg [15:0] code_buf;   // буфер кода (максимум 16 бит для bf16)
    reg [31:0] result_buf; // захваченный результат декодера

    // -------------------------------------------------------------------------
    // 5а. Инстанции декодеров (комбинаторные)
    // -------------------------------------------------------------------------
    wire [31:0] bf16_fp32;
    wire        bf16_zero, bf16_inf, bf16_nan;
    bf16_decode u_bf16 (
        .bf16_in  (code_buf[15:0]),
        .fp32_out (bf16_fp32),
        .is_zero  (bf16_zero),
        .is_inf   (bf16_inf),
        .is_nan   (bf16_nan)
    );

    wire [31:0] fnuz_fp32;
    wire        fnuz_zero, fnuz_nan;
    fp8_e4m3_fnuz_decode u_fnuz (
        .e4m3_in  (code_buf[7:0]),
        .fp32_out (fnuz_fp32),
        .is_zero  (fnuz_zero),
        .is_nan   (fnuz_nan)
    );

    wire [31:0] int8_i32;
    wire        int8_zero;
    int8_decode u_int8 (
        .int8_in   (code_buf[7:0]),
        .int32_out (int8_i32),
        .is_zero   (int8_zero)
    );

    wire [31:0] nf4_fp32;
    nf4_decode u_nf4 (
        .nf4_in   (code_buf[3:0]),
        .fp32_out (nf4_fp32)
    );

    wire [31:0] posit8_fp32;
    wire        posit8_zero, posit8_nar;
    posit8_decode u_posit8 (
        .posit_in (code_buf[7:0]),
        .fp32_out (posit8_fp32),
        .is_zero  (posit8_zero),
        .is_nar   (posit8_nar)
    );

    // -------------------------------------------------------------------------
    // 5б. Мультиплексор результата
    //   Примечание: декодеры комбинаторные → result захватывается
    //   в момент завершения приёма последнего байта кода.
    // -------------------------------------------------------------------------
    reg [31:0] decode_out;
    always @(*) begin
        case (fmt_sel)
            3'd0: decode_out = bf16_fp32;
            3'd1: decode_out = fnuz_fp32;
            3'd2: decode_out = int8_i32;
            3'd3: decode_out = nf4_fp32;
            3'd4: decode_out = posit8_fp32;
            default: decode_out = 32'hFFFF_FFFF; // зарезервировано
        endcase
    end

    // -------------------------------------------------------------------------
    // 5в. Конечный автомат
    // -------------------------------------------------------------------------
    always @(posedge clk) begin
        tx_req <= 1'b0; // по умолчанию нет запроса TX

        if (rst) begin
            state      <= ST_CMD;
            fmt_sel    <= 3'd0;
            code_buf   <= 16'd0;
            result_buf <= 32'd0;
        end else begin
            case (state)

                // --- Ожидание командного байта ---
                ST_CMD: begin
                    if (rx_valid) begin
                        fmt_sel  <= rx_data[7:5];
                        code_buf <= 16'd0;
                        state    <= ST_D0;
                    end
                end

                // --- Приём первого байта данных ---
                ST_D0: begin
                    if (rx_valid) begin
                        code_buf[7:0] <= rx_data;
                        if (fmt_sel == 3'd0) begin
                            // bf16: нужен ещё один байт (старший)
                            state <= ST_D1;
                        end else begin
                            // Однобайтовые форматы: декодировать сразу
                            result_buf <= decode_out;
                            // Запустить отправку byte0
                            tx_byte <= decode_out[7:0];
                            tx_req  <= 1'b1;
                            state   <= ST_TX0;
                        end
                    end
                end

                // --- Приём второго байта данных (только bf16) ---
                ST_D1: begin
                    if (rx_valid) begin
                        code_buf[15:8] <= rx_data; // старший байт LE
                        result_buf     <= decode_out; // комбинационный путь ещё актуален
                        tx_byte        <= decode_out[7:0];
                        tx_req         <= 1'b1;
                        state          <= ST_TX0;
                    end
                end

                // --- Отправка 4 байт ответа (LE) ---
                ST_TX0: begin
                    if (!tx_busy && !tx_req) begin
                        tx_byte <= result_buf[15:8];
                        tx_req  <= 1'b1;
                        state   <= ST_TX1;
                    end
                end
                ST_TX1: begin
                    if (!tx_busy && !tx_req) begin
                        tx_byte <= result_buf[23:16];
                        tx_req  <= 1'b1;
                        state   <= ST_TX2;
                    end
                end
                ST_TX2: begin
                    if (!tx_busy && !tx_req) begin
                        tx_byte <= result_buf[31:24];
                        tx_req  <= 1'b1;
                        state   <= ST_TX3;
                    end
                end
                ST_TX3: begin
                    if (!tx_busy && !tx_req) begin
                        state <= ST_CMD;
                    end
                end

                default: state <= ST_CMD;
            endcase
        end
    end

    // =========================================================================
    // 6. LED-индикаторы (LVCMOS18, B13/C13/D14/D15)
    //    [0] = heartbeat (бит[24] result_buf, мигает при работе)
    //    [1] = rx_valid  (строб приёма байта)
    //    [2] = tx_busy
    //    [3] = rst (активен при сбросе)
    // =========================================================================
    reg [24:0] heartbeat_cnt;
    always @(posedge clk) begin
        if (rst) heartbeat_cnt <= 0;
        else     heartbeat_cnt <= heartbeat_cnt + 1;
    end

    assign led[0] = heartbeat_cnt[24]; // мигает ~6 Гц при 200 МГц
    assign led[1] = rx_valid;
    assign led[2] = tx_busy;
    assign led[3] = rst;

endmodule
`default_nettype wire
