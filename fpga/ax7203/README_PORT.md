# decode-HW Findings: перенос Corona на 7-series (ТРЕК B)

**Автор:** Vasilev  
**Дата подготовки:** 2026-06-28  
**Репозиторий:** gHashTag/tt-trinity-corona (ветка main)  
**Issues:** gHashTag/trinity-fpga #200–204  
**Цель:** подготовить RTL + обвязку для синтеза и прошивки на ALINX AX7203 (xc7a200tfbg484-2).

> **HONESTY NOTICE:**  
> Decode-HW счётчик остаётся **0/83** до реального прогона на железе.  
> Синтез и прошивка — **[ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]**.  
> Encoding ≠ compute ≠ FPGA-decode. Артефакты готовы, но корректность на железе не доказана до timing-closure и аппаратного conformance-прогона.

---

## 1. Карта декодеров

### 1.1 bf16_decode (issue #200)

| Параметр | Значение |
|---|---|
| Файл | `src/rtl/bf16_decode.v` |
| Вход | `bf16_in [15:0]` (16 бит) |
| Выход | `fp32_out [31:0]` (32 бит FP32) |
| Флаги | `is_zero`, `is_inf`, `is_nan` |
| Латентность | Комбинаторная (0 тактов) |
| Логика | `fp32_out = {bf16_in, 16'b0}` — BF16 это просто старшие 16 бит FP32 |
| Спец-значения | NaN: exp=0xFF, mant≠0; Inf: exp=0xFF, mant=0; Zero: exp=0, mant=0 |
| Зависимость от format_rom | Нет |
| Протокол (AX7203) | sel=0, 2 байта кода LE |

### 1.2 fp8_e4m3_fnuz_decode (issue #201)

| Параметр | Значение |
|---|---|
| Файл | `src/rtl/fp8_e4m3_fnuz_decode.v` |
| Вход | `e4m3_in [7:0]` (8 бит) |
| Выход | `fp32_out [31:0]` (32 бит FP32) |
| Флаги | `is_zero`, `is_nan` |
| Латентность | Комбинаторная (always @(*), 0 тактов) |
| Спец-значения | 0x00=+0 (не 0x80!); 0x80=NaN; нет Inf (FNUZ = Finite-Unsigned-Zero) |
| Формат | AMD MI300/CDNA3: bias=8, E4M3, знак в bit[7], но 0x80 резервирован под NaN |
| Субнормали | Да (exp=0, mant≠0 → денормализованные значения с bias-сдвигом) |
| Зависимость от format_rom | Нет |
| Протокол (AX7203) | sel=1, 1 байт кода |

### 1.3 int8_decode (issue #202)

| Параметр | Значение |
|---|---|
| Файл | `src/rtl/int8_decode.v` |
| Вход | `int8_in [7:0]` (8 бит, знаковое 2's complement) |
| Выход | `int32_out [31:0]` (32 бит, знаковое расширение) |
| Флаги | `is_zero` |
| Латентность | Комбинаторная (0 тактов) |
| Логика | `int32_out = {{24{int8_in[7]}}, int8_in}` |
| Спец-значения | Нет (−128..+127, нет NaN/Inf) |
| Зависимость от format_rom | Нет |
| Протокол (AX7203) | sel=2, 1 байт кода |
| Замечание | Выход — целое число, не FP32. UART возвращает raw int32 LE |

### 1.4 nf4_decode (issue #203)

| Параметр | Значение |
|---|---|
| Файл | `src/rtl/nf4_decode.v` |
| Вход | `nf4_in [3:0]` (4 бита, 16 кодов) |
| Выход | `fp32_out [31:0]` (32 бит FP32) |
| Латентность | Комбинаторная (casez LUT, 0 тактов) |
| Спец-значения | Нет (чистый LUT, нет IEEE спец-значений в NF4) |
| Значения | Квантили N(0,1): −1.0 .. +1.0, 16 уровней |
| Зависимость от format_rom | Нет (LUT захардкожен в RTL) |
| Протокол (AX7203) | sel=3, 1 байт кода (нижние 4 бита используются) |

### 1.5 posit8_decode (issue #204)

| Параметр | Значение |
|---|---|
| Файл | `src/rtl/posit8_decode.v` |
| Вход | `posit_in [7:0]` (8 бит) |
| Выход | `fp32_out [31:0]` (32 бит FP32) |
| Флаги | `is_zero`, `is_nar` |
| Латентность | Комбинаторная (casez LZC + арифметика, 0 тактов) |
| Спец-значения | 0x00=+0; 0x80=NaR (Not a Real) → отображается в 0x7FC00000 (NaN) |
| Параметры | posit8(es=0): useed=2, диапазон ≈ [2^{−6} .. 64] |
| Логика | Знак → 2's complement → LZC (7 бит) → режим k → fraction → FP32 |
| Зависимость от format_rom | Нет |
| Протокол (AX7203) | sel=4, 1 байт кода |

---

## 2. Топология top-модуля (corona_decode_top_ax7203.v)

### 2.1 Схема сигнального пути

```
sys_clk_p/n (LVDS R4/T4)
  └─ IBUFDS (DIFF_SSTL15, no internal termination)
       └─ BUFG
            └─ clk (200 МГц глобальная сеть)

sys_rst_n (T6, LVCMOS15, active-low)
  └─ 2-ступенчатый синхронизатор (rst_meta → rst_sync)
       └─ rst (active-high внутри)

uart_rx (P20, LVCMOS33)
  └─ 2-ступенчатый синхронизатор (rx_meta → rx_in)
       └─ UART RX FSM (BAUD_DIV=1736)
            └─ rx_data [7:0], rx_valid

rx_data → CMD FSM (3-бит fmt_sel + 1..2 байт кода) → code_buf [15:0]
  └─ bf16_decode (code_buf[15:0])
  └─ fp8_e4m3_fnuz_decode (code_buf[7:0])
  └─ int8_decode (code_buf[7:0])
  └─ nf4_decode (code_buf[3:0])
  └─ posit8_decode (code_buf[7:0])
         ↑ все комбинаторные, параллельны
  └─ Мультиплексор по fmt_sel → result_buf [31:0]
       └─ UART TX FSM → uart_tx (N15) [4 байта LE]

LEDs B13/C13/D14/D15 (LVCMOS18):
  led[0] = heartbeat (heartbeat_cnt[24], ~6 Гц)
  led[1] = rx_valid (строб приёма байта)
  led[2] = tx_busy
  led[3] = rst (активен при сбросе)
```

### 2.2 UART-протокол (115200 8N1, CP2102N)

**Запрос (хост → FPGA):**

| Байт | Биты | Значение |
|---|---|---|
| 0 (CMD) | [7:5] | fmt_sel: 0=bf16, 1=fp8_e4m3_fnuz, 2=int8, 3=nf4, 4=posit8, 5–7=reserved |
| 0 (CMD) | [4:0] | 0x00 (зарезервировано) |
| 1 | [7:0] | Младший байт кода (для всех форматов) |
| 2 | [7:0] | Старший байт кода (только для bf16; другие форматы: не отправляется) |

**Ответ (FPGA → хост): 4 байта LE**

| Байт | Значение |
|---|---|
| 0 | result[7:0] |
| 1 | result[15:8] |
| 2 | result[23:16] |
| 3 | result[31:24] |

Для int8: result = int32 (знаковое расширение). Для остальных: result = fp32 binary representation.

### 2.3 Тайминг UART при 200 МГц

- BAUD_DIV = 1736 → реальная скорость = 200 000 000 / 1736 ≈ 115 207 бод (погрешность < 0.01%)
- Время одного байта ≈ 86.8 мкс
- Время транзакции bf16: 3 байта запроса + 4 байта ответа = 607 мкс (без задержки декодера)
- Время транзакции 8-бит форматов: 2 + 4 = 521 мкс

---

## 3. Зависимости от TinyTapeout и что изменено

### 3.1 TinyTapeout-специфичное (удалено/заменено)

| Элемент TT | Причина замены | Замена в AX7203 |
|---|---|---|
| `tt_um_trinity_corona.v` | 8-бит параллельный интерфейс ui_in/uo_out, GF180MCU pinout | `corona_decode_top_ax7203.v` с UART |
| `ena` gate (TT-специфичный | Не существует на дискретной FPGA | Удалён (всегда active) |
| Параллельный протокол v2 (CMD→CMD2→DATA→STATUS) | Заточен под 8-бит шину с clk-per-byte | Заменён UART-протоколом |
| ROM readback (format_rom через uo_out) | Необязателен для decode-HW тестирования | Не инстанцирован в top (format_rom.v остаётся для Vivado read_verilog) |
| GF180MCU IO (LVCMOS3.3 по умолчанию) | 7-series требует явного IOSTANDARD | XDC с DIFF_SSTL15/LVCMOS15/LVCMOS33/LVCMOS18 |

### 3.2 Что сохранено без изменений

- Все 5 декодеров: `bf16_decode.v`, `fp8_e4m3_fnuz_decode.v`, `int8_decode.v`, `nf4_decode.v`, `posit8_decode.v` — исходники из репо, без патчей.
- `format_rom.v` — инклюдится в Vivado (чтобы не было ошибок, если top.v ссылается), но не инстанцируется в новом top.

---

## 4. Пошаговая инструкция: синтез → прошивка → проверка

> Все шаги ниже требуют локальной установки Vivado и openocd.  
> Артефакты RTL/XDC/Python подготовлены в `/decode_hw_track/`.

### Шаг 1. Подготовка файлов [ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]

Скопируйте из репо `gHashTag/tt-trinity-corona` (ветка main) следующие файлы в рабочую директорию:

```
src/rtl/bf16_decode.v
src/rtl/fp8_e4m3_fnuz_decode.v
src/rtl/int8_decode.v
src/rtl/nf4_decode.v
src/rtl/posit8_decode.v
src/rtl/format_rom.v
```

Плюс файлы из `decode_hw_track/`:
```
corona_decode_top_ax7203.v
corona_decode_ax7203.xdc
corona_decode_host.py
```

### Шаг 2. Синтез в Vivado (TCL) [ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]

Запустите Vivado в batch-режиме (`vivado -mode batch -source synth.tcl`) со следующим TCL:

```tcl
# synth.tcl — синтез corona decode для AX7203
create_project corona_decode ./corona_decode_proj -part xc7a200tfbg484-2 -force

# Исходники RTL
read_verilog bf16_decode.v
read_verilog fp8_e4m3_fnuz_decode.v
read_verilog int8_decode.v
read_verilog nf4_decode.v
read_verilog posit8_decode.v
read_verilog format_rom.v
read_verilog corona_decode_top_ax7203.v

# Constraints
read_xdc corona_decode_ax7203.xdc

# Синтез
synth_design -top corona_decode_top_ax7203 -part xc7a200tfbg484-2 -flatten_hierarchy rebuilt

# Проверка ресурсов (должно быть << 134600 LUT / 740 DSP / 365 BRAM)
report_utilization -file utilization.rpt

# Оптимизация и размещение
opt_design
place_design
phys_opt_design

# Routing
route_design

# КРИТИЧНО: проверить timing перед прошивкой
report_timing_summary -file timing_summary.rpt
# Если WNS < 0 → добавить MMCM (см. Риски ниже)

# Битстрим
write_bitstream -force corona_decode_ax7203.bit
```

**Ожидаемые ресурсы (оценка):** < 500 LUT6, 0 BRAM, 0 DSP — все декодеры комбинаторные.

### Шаг 3. Проверка IDCODE перед прошивкой [ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]

```bash
# Подключить JTAG (встроенный или Digilent HS2)
openocd -f interface/ftdi/digilent_hs2.cfg -f target/xilinx-xc7.cfg \
  -c "init; scan_chain; shutdown"
```

В выводе должна быть строка:
```
xc7a200t.tap: IDCODE 0x13636093
```

**КРИТИЧНО:** если IDCODE = `0x0362D093` — это другая плата (QMTECH). Прошивать нельзя.

### Шаг 4. Прошивка [ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]

```bash
openocd -f interface/ftdi/digilent_hs2.cfg -f target/xilinx-xc7.cfg \
  -c "init; pld load 0 corona_decode_ax7203.bit; shutdown"
```

Успешная загрузка: LED[3] (D15, rst) должен погаснуть, LED[0] (B13) должен мигать ~6 Гц.

### Шаг 5. Аппаратный conformance-тест [ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ]

```bash
# Установить зависимость (если не установлен pyserial)
pip install pyserial

# Синтетический самотест (проверка логики без железа)
python corona_decode_host.py --self-test

# Аппаратный тест через CP2102N (/dev/cu.usbserial-120 macOS;
# на Linux обычно /dev/ttyUSB0)
python corona_decode_host.py --port /dev/cu.usbserial-120

# Или явно указать порт и скорость
python corona_decode_host.py --port /dev/ttyUSB0 --baud 115200
```

**Критерий успеха:** все 51+ тест-кейс = PASS → decode-HW ячейки 0→5 считаются пройденными.

---

## 5. Связь с issues #200–204

| Issue | Формат | Файл RTL | sel в протоколе |
|---|---|---|---|
| #200 | bf16 | bf16_decode.v | 3'b000 |
| #201 | fp8_e4m3_fnuz | fp8_e4m3_fnuz_decode.v | 3'b001 |
| #202 | int8 | int8_decode.v | 3'b010 |
| #203 | nf4 | nf4_decode.v | 3'b011 |
| #204 | posit8 | posit8_decode.v | 3'b100 |

Все 5 декодеров существуют в репо (проверено чтением через `gh api`), являются чисто комбинаторными и не зависят от `format_rom.v` (только top TinyTapeout инстанцировал ROM для параллельного ROM-readback-режима).

---

## 6. Риски и ограничения

### 6.1 LVDS клок без PLL/MMCM — джиттер не скомпенсирован [КРИТИЧНО]

AX7203 использует LVDS 200 МГц. Текущий top использует только `IBUFDS → BUFG` без MMCM/PLL.

- **Риск:** Vivado может не достичь timing closure при 200 МГц без PLL. WNS < 0 = функциональные ошибки при реальном прогоне.
- **Признак проблемы:** в `timing_summary.rpt` после `route_design` строка `WNS: < 0.000 ns`.
- **Решение:** добавить `MMCM` с `CLKIN_PERIOD = 5.0` (200 МГц) и `CLKOUT0_DIVIDE_F = 2.0` (→ 100 МГц), чтобы уменьшить нагрузку. Для декодеров это не проблема (они комбинаторные), но UART RX/TX требует стабильного клока.
- **Текущий статус:** IBUFDS → BUFG достаточно для первоначального тестирования при условии WNS ≥ 0. Если WNS < 0 → файл остаётся подготовленным, но требует добавления MMCM.

### 6.2 Setup/hold не доказаны до реального прогона

Статический timing analysis Vivado — необходимое, но не достаточное условие. Реальный джиттер, температурные/вольтажные вариации и PCB-паразиты могут нарушить timing. Декларация прохождения тестов возможна только после фактического аппаратного conformance-прогона с WNS ≥ 0 ns и WHS ≥ 0 ns.

### 6.3 BAUD_DIV = 1736 точность

200 000 000 / 1736 = 115 207.4 бод. Погрешность ~0.007% — в пределах допуска UART (±2%). CP2102N на другом конце работает на 115200 бод точно. Расхождение 7 Гц при 10 бит/символ: ошибка накапливается ~0.06% за символ → при 8 бит данных промах < 0.5 бит. Проблем нет.

### 6.4 IOSTANDARD LEDs: LVCMOS18, не LVCMOS33

**Это критично.** На AX7203 банк LED (B13/C13/D14/D15) питается от 1.8 В. Задание LVCMOS33 повредит банк. XDC использует LVCMOS18 — именно как на AX7203 (не путать с QMTECH AX7203B, где может быть иначе).

### 6.5 format_rom.v в Vivado read_verilog

`format_rom.v` нужно добавить в `read_verilog` (см. Шаг 2 TCL) даже если он не инстанцируется в новом top — иначе Vivado может выдать предупреждение о незакрытых зависимостях при анализе источников. Модуль не будет синтезирован (нет инстанции в top), но его наличие в проекте не вредит.

### 6.6 Decode-HW счётчик

Декодеры **закодированы** в RTL и **переносятся** на 7-series — это encoding/porting. **Compute** не выполнен. **FPGA-decode** — не подтверждён до реального прогона на железе. Счётчик decode-HW остаётся 0/83 до успешного conformance-прогона с результатом PASS на каждом из 5 форматов.

---

## 7. Список артефактов

| Файл | Назначение |
|---|---|
| `corona_decode_top_ax7203.v` | Новый top для AX7203: IBUFDS, UART, 5 декодеров, LED |
| `corona_decode_ax7203.xdc` | Pin assignments, clock, IOSTANDARD, false_path |
| `corona_decode_host.py` | Conformance-скрипт + синтетический самотест (51 PASS) |
| `decode_hw_findings.md` | Этот документ |

**Исходники декодеров (из репо, не изменены):**

| Файл | Issue |
|---|---|
| `src/rtl/bf16_decode.v` | #200 |
| `src/rtl/fp8_e4m3_fnuz_decode.v` | #201 |
| `src/rtl/int8_decode.v` | #202 |
| `src/rtl/nf4_decode.v` | #203 |
| `src/rtl/posit8_decode.v` | #204 |
| `src/rtl/format_rom.v` | (зависимость top) |
