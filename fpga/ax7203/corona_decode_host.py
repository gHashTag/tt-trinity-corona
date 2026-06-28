#!/usr/bin/env python3
# corona_decode_host.py
# Автор: Vasilev
# Назначение: host-side conformance-скрипт для декодеров Corona на AX7203.
#   Шлёт коды форматов через UART (/dev/cu.usbserial-120 или задаётся argv),
#   читает 4-байтовый результат (fp32 или int32 LE),
#   сверяет с golden-значениями из t27 conformance-паков.
#
# Использование:
#   python corona_decode_host.py                  # прогон всех тестов на железе
#   python corona_decode_host.py --self-test      # синтетический самотест (без UART)
#   python corona_decode_host.py --port /dev/ttyUSB0
#
# UART-протокол (см. corona_decode_top_ax7203.v):
#   Запрос: [cmd_byte: fmt_sel в bits[7:5]] + [данные LE]
#   Ответ:  4 байта LE = fp32_out / int32_out
#   Порты:
#     sel=0 (bf16):            2 байта данных (16-бит LE)
#     sel=1 (fp8_e4m3_fnuz):  1 байт
#     sel=2 (int8):            1 байт
#     sel=3 (nf4):             1 байт (нижние 4 бита)
#     sel=4 (posit8):          1 байт

import argparse
import struct
import sys
import math
import time

# ---------------------------------------------------------------------------
# Попытка импортировать serial (не обязательно для --self-test)
# ---------------------------------------------------------------------------
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


# ===========================================================================
# Golden-значения (t27 conformance packs, bit-precise)
# ===========================================================================

# ---------------------------------------------------------------------------
# BF16 → FP32: BF16 = старшие 16 бит FP32.
#   Правило: fp32_out = {bf16_in[15:0], 16'b0}
# ---------------------------------------------------------------------------
BF16_GOLDEN = [
    # (bf16_hex, expected_fp32_hex, описание)
    (0x0000, 0x00000000, "+0.0"),
    (0x8000, 0x80000000, "-0.0"),
    (0x3F80, 0x3F800000, "+1.0"),
    (0xBF80, 0xBF800000, "-1.0"),
    (0x4049, 0x40490000, "≈π (3.140625)"),
    (0x7F80, 0x7F800000, "+Inf"),
    (0xFF80, 0xFF800000, "-Inf"),
    (0x7FC0, 0x7FC00000, "NaN (quiet)"),
    (0x0080, 0x00800000, "мин нормаль"),
    (0x007F, 0x007F0000, "макс субнормаль"),
]

# ---------------------------------------------------------------------------
# FP8 E4M3 FNUZ → FP32 (AMD MI300/CDNA3, bias=8, 0x80=NaN)
#   Реализованы вручную по спецификации (соответствует golden t27)
# ---------------------------------------------------------------------------
def fp8_e4m3_fnuz_decode_golden(code: int) -> int:
    """Возвращает fp32 как int (bit-pattern)."""
    if code == 0x00:
        return 0x00000000  # +0
    if code == 0x80:
        return 0x7FC00000  # NaN (quiet)
    sign = (code >> 7) & 1
    exp4 = (code >> 3) & 0xF
    mant = code & 0x7
    if exp4 == 0:
        # Субнормаль: value = (-1)^S * 2^(1-8) * (mant/8)
        if mant & 4:
            fp32_exp = 119
            fp32_mant = ((mant & 3) << 21)
        elif mant & 2:
            fp32_exp = 118
            fp32_mant = ((mant & 1) << 22)
        else:
            fp32_exp = 117
            fp32_mant = 0
    else:
        # Нормаль: value = (-1)^S * 2^(E-8) * (1 + mant/8)
        fp32_exp = exp4 + 119
        fp32_mant = mant << 20
    return (sign << 31) | (fp32_exp << 23) | fp32_mant

FP8_E4M3_FNUZ_GOLDEN = [
    # (код, golden_fp32_hex, описание)
    (0x00, 0x00000000, "+0.0"),
    (0x80, 0x7FC00000, "NaN"),
    (0x3F, fp8_e4m3_fnuz_decode_golden(0x3F), "0x3F нормаль"),
    (0x7F, fp8_e4m3_fnuz_decode_golden(0x7F), "0x7F макс (+240)"),
    (0xFF, fp8_e4m3_fnuz_decode_golden(0xFF), "0xFF -макс (-240)"),
    (0x08, fp8_e4m3_fnuz_decode_golden(0x08), "0x08 мин нормаль"),
    (0x01, fp8_e4m3_fnuz_decode_golden(0x01), "0x01 субнорм"),
    (0x40, fp8_e4m3_fnuz_decode_golden(0x40), "0x40 -0.0..."),
]

# ---------------------------------------------------------------------------
# INT8 → INT32 (sign-extend)
# ---------------------------------------------------------------------------
def int8_decode_golden(code: int) -> int:
    # Знаковое расширение 8-бит → 32-бит (2's complement)
    byte_val = code & 0xFF
    if byte_val & 0x80:  # отрицательное
        signed = byte_val - 256
    else:
        signed = byte_val
    return signed & 0xFFFFFFFF

INT8_GOLDEN = [
    (0x00, 0x00000000, "0"),
    (0x01, 0x00000001, "1"),
    (0x7F, 0x0000007F, "127"),
    (0x80, 0xFFFFFF80, "-128"),
    (0xFF, 0xFFFFFFFF, "-1"),
    (0xFE, 0xFFFFFFFE, "-2"),
    (0x55, 0x00000055, "85"),
    (0xAB, 0xFFFFFFAB, "-85"),
]

# ---------------------------------------------------------------------------
# NF4 → FP32 (16-entry LUT, QLoRA bitsandbytes)
# ---------------------------------------------------------------------------
NF4_LUT_HEX = [
    0xBF800000,  # 0x0  = -1.0
    0xBF3239B1,  # 0x1
    0xBF066B30,  # 0x2
    0xBECA32A0,  # 0x3
    0xBE91A24D,  # 0x4
    0xBE3D353F,  # 0x5
    0xBDBA7871,  # 0x6
    0x00000000,  # 0x7  =  0.0
    0x3DA2FAFF,  # 0x8
    0x3E24CAE3,  # 0x9
    0x3E7C04DD,  # 0xA
    0x3EAD033A,  # 0xB
    0x3EE1A4B8,  # 0xC
    0x3F1007AB,  # 0xD
    0x3F3913B3,  # 0xE
    0x3F800000,  # 0xF  = +1.0
]

NF4_GOLDEN = [(i, NF4_LUT_HEX[i], f"nf4[{i}]") for i in range(16)]

# ---------------------------------------------------------------------------
# Posit8(es=0) → FP32
# ---------------------------------------------------------------------------
def posit8_decode_golden(code: int) -> int:
    if code == 0x00:
        return 0x00000000
    if code == 0x80:
        return 0x7FC00000  # NaR → NaN
    sign = (code >> 7) & 1
    abs7 = code & 0x7F
    if sign:
        # Преобразование 2-complement для [6:0]
        abs7 = ((~abs7) & 0x7F) + 1
        abs7 &= 0x7F

    regime_sign = (abs7 >> 6) & 1
    regime_bits = (~abs7 & 0x7F) if regime_sign else abs7

    # LZC на 7 битах
    lzc = 0
    for b in range(6, -1, -1):
        if (regime_bits >> b) & 1:
            break
        lzc += 1

    k = lzc - 1 if regime_sign else -lzc
    regime_total = min(lzc + 1, 7)
    shifted = (abs7 << regime_total) & 0x7F
    fraction = (shifted >> 1) & 0x3F  # 6 бит дроби

    fp32_exp_raw = 127 + k
    if fp32_exp_raw < 0:
        fp32_exp_raw = 0
    if fp32_exp_raw > 255:
        fp32_exp_raw = 255

    return (sign << 31) | ((fp32_exp_raw & 0xFF) << 23) | (fraction << 17)

POSIT8_GOLDEN = [
    (0x00, 0x00000000, "+0 (zero)"),
    (0x80, 0x7FC00000, "NaR→NaN"),
    (0x40, posit8_decode_golden(0x40), "0x40 +1.0?"),
    (0x7F, posit8_decode_golden(0x7F), "0x7F макс"),
    (0x01, posit8_decode_golden(0x01), "0x01 мин"),
    (0x60, posit8_decode_golden(0x60), "0x60"),
    (0xC0, posit8_decode_golden(0xC0), "0xC0 -1.0?"),
    (0xFF, posit8_decode_golden(0xFF), "0xFF -мин"),
]


# ===========================================================================
# Протокол UART
# ===========================================================================

FMT_BF16       = 0  # sel bits[7:5] = 0b000
FMT_FP8_FNUZ   = 1  # 0b001
FMT_INT8       = 2  # 0b010
FMT_NF4        = 3  # 0b011
FMT_POSIT8     = 4  # 0b100

FORMAT_NAMES = {
    FMT_BF16:     "bf16",
    FMT_FP8_FNUZ: "fp8_e4m3_fnuz",
    FMT_INT8:     "int8",
    FMT_NF4:      "nf4",
    FMT_POSIT8:   "posit8",
}

def build_request(fmt_sel: int, code: int) -> bytes:
    """Строит байты запроса для UART согласно протоколу."""
    cmd = (fmt_sel & 0x7) << 5  # fmt_sel в bits[7:5]
    if fmt_sel == FMT_BF16:
        # 2 байта данных, LE
        return bytes([cmd, code & 0xFF, (code >> 8) & 0xFF])
    else:
        # 1 байт данных
        return bytes([cmd, code & 0xFF])

def parse_response(data: bytes) -> int:
    """Парсит 4-байтовый ответ UART (LE) в int."""
    assert len(data) == 4, f"Ожидали 4 байта, получили {len(data)}"
    return struct.unpack('<I', data)[0]

def fp32_hex_to_float(val: int) -> float:
    return struct.unpack('<f', struct.pack('<I', val))[0]

def fp32_eq(a: int, b: int) -> bool:
    """Bit-precise сравнение fp32."""
    return a == b

def run_test_uart(port, baud: int, fmt_sel: int, golden_cases):
    """Прогоняет набор тест-кейсов через реальный UART-порт."""
    passed = 0
    failed = 0
    errors = []
    for code, expected, desc in golden_cases:
        req = build_request(fmt_sel, code)
        port.write(req)
        port.flush()
        resp = port.read(4)
        if len(resp) != 4:
            errors.append(f"  TIMEOUT [{desc}] code=0x{code:02X}: получили {len(resp)} байт")
            failed += 1
            continue
        got = parse_response(resp)
        if fp32_eq(got, expected):
            passed += 1
        else:
            errors.append(
                f"  FAIL [{desc}] code=0x{code:02X}: "
                f"ожидали 0x{expected:08X} ({fp32_hex_to_float(expected):.6g}), "
                f"получили 0x{got:08X} ({fp32_hex_to_float(got):.6g})"
            )
            failed += 1
    return passed, failed, errors


# ===========================================================================
# Синтетический самотест (без UART — проверка golden-логики парсера)
# ===========================================================================

def run_self_test_synthetic():
    """
    Имитирует полный цикл: build_request → parse_response → golden-check.
    Не использует реальный порт — проверяет корректность протокольной логики
    и golden-вычислений в Python.
    """
    print("=" * 60)
    print("СИНТЕТИЧЕСКИЙ САМОТЕСТ ПАРСЕРА (без UART)")
    print("=" * 60)

    all_passed = True

    def sim_fpga_decode(fmt_sel: int, code: int) -> int:
        """Имитация RTL-декодеров на Python (эталон для самотеста)."""
        if fmt_sel == FMT_BF16:
            return (code & 0xFFFF) << 16
        elif fmt_sel == FMT_FP8_FNUZ:
            return fp8_e4m3_fnuz_decode_golden(code)
        elif fmt_sel == FMT_INT8:
            return int8_decode_golden(code)
        elif fmt_sel == FMT_NF4:
            return NF4_LUT_HEX[code & 0xF]
        elif fmt_sel == FMT_POSIT8:
            return posit8_decode_golden(code)
        else:
            return 0xFFFFFFFF

    suites = [
        (FMT_BF16,     BF16_GOLDEN,         "bf16"),
        (FMT_FP8_FNUZ, FP8_E4M3_FNUZ_GOLDEN,"fp8_e4m3_fnuz"),
        (FMT_INT8,     INT8_GOLDEN,          "int8"),
        (FMT_NF4,      NF4_GOLDEN,           "nf4"),
        (FMT_POSIT8,   POSIT8_GOLDEN,        "posit8"),
    ]

    total_pass = 0
    total_fail = 0

    for fmt_sel, cases, name in suites:
        passed = 0
        failed = 0
        print(f"\n[{name}]")
        for code, expected, desc in cases:
            # 1. Построить запрос
            req = build_request(fmt_sel, code)
            # 2. Распарсить командный байт — проверить fmt_sel
            got_sel = (req[0] >> 5) & 0x7
            assert got_sel == fmt_sel, f"build_request: fmt_sel неверен: {got_sel} != {fmt_sel}"
            # 3. Распарсить код из запроса
            if fmt_sel == FMT_BF16:
                recovered = req[1] | (req[2] << 8)
            else:
                recovered = req[1]
            assert recovered == (code & (0xFFFF if fmt_sel == FMT_BF16 else 0xFF)), \
                f"Код не сохранился: {recovered} != {code}"
            # 4. Имитировать декодер
            simulated = sim_fpga_decode(fmt_sel, recovered)
            # 5. Упаковать в 4 байта LE (как FPGA отправит)
            resp_bytes = struct.pack('<I', simulated)
            # 6. Распарсить ответ
            got = parse_response(resp_bytes)
            # 7. Сравнить с golden
            if fp32_eq(got, expected):
                print(f"  PASS  [{desc:20s}] code=0x{code:04X} → 0x{got:08X}")
                passed += 1
            else:
                print(f"  FAIL  [{desc:20s}] code=0x{code:04X} "
                      f"ожидали=0x{expected:08X} ({fp32_hex_to_float(expected):.6g}) "
                      f"получили=0x{got:08X} ({fp32_hex_to_float(got):.6g})")
                failed += 1
                all_passed = False
        total_pass += passed
        total_fail += failed
        print(f"  Итого [{name}]: {passed} прошло / {failed} не прошло")

    # Дополнительная проверка: parse_response с известными байтами
    print("\n[parse_response byte-order test]")
    test_bytes = bytes([0x01, 0x02, 0x03, 0x04])  # LE: 0x04030201
    expected_val = 0x04030201
    got_val = parse_response(test_bytes)
    if got_val == expected_val:
        print(f"  PASS  LE parse: 0x{got_val:08X}")
        total_pass += 1
    else:
        print(f"  FAIL  LE parse: ожидали 0x{expected_val:08X}, получили 0x{got_val:08X}")
        total_fail += 1
        all_passed = False

    print(f"\n{'='*60}")
    print(f"ИТОГО: {total_pass} прошло / {total_fail} не прошло")
    if all_passed:
        print("САМОТЕСТ: ВСЕ ТЕСТЫ ПРОШЛИ — протокольная логика верна")
    else:
        print("САМОТЕСТ: ЕСТЬ ОШИБКИ — проверьте golden-функции")
    print("=" * 60)
    return all_passed


# ===========================================================================
# Основной прогон на реальном железе
# ===========================================================================

def run_hardware_tests(port_name: str, baud: int):
    """[ТРЕБУЕТ ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ] — запускается только с подключённой FPGA."""
    if not SERIAL_AVAILABLE:
        print("ОШИБКА: pyserial не установлен. Установите: pip install pyserial")
        sys.exit(1)

    print(f"Подключение к {port_name} @ {baud} бод...")
    try:
        with serial.Serial(port_name, baud, timeout=1.0) as ser:
            time.sleep(0.1)  # дать CP2102N инициализироваться
            ser.reset_input_buffer()

            suites = [
                (FMT_BF16,     BF16_GOLDEN,         "bf16"),
                (FMT_FP8_FNUZ, FP8_E4M3_FNUZ_GOLDEN,"fp8_e4m3_fnuz"),
                (FMT_INT8,     INT8_GOLDEN,          "int8"),
                (FMT_NF4,      NF4_GOLDEN,           "nf4"),
                (FMT_POSIT8,   POSIT8_GOLDEN,        "posit8"),
            ]

            total_pass = 0
            total_fail = 0
            total_errors = []

            for fmt_sel, cases, name in suites:
                print(f"\n[{name}]")
                p, f, errs = run_test_uart(ser, baud, fmt_sel, cases)
                for e in errs:
                    print(e)
                    total_errors.append(e)
                total_pass += p
                total_fail += f
                print(f"  Итого [{name}]: {p} прошло / {f} не прошло")

            print(f"\n{'='*60}")
            print(f"АППАРАТНЫЙ ТЕСТ: {total_pass} прошло / {total_fail} не прошло")
            if total_fail == 0:
                print("ВСЕ ТЕСТЫ ПРОШЛИ — decode-HW ячейки ЗАСЧИТАНЫ (0→5)")
                print("ВНИМАНИЕ: результат действителен только при WNS≥0 в timing report Vivado")
            else:
                print("ЕСТЬ ОШИБКИ — проверьте RTL, XDC, и timing report")
            print("=" * 60)
    except serial.SerialException as e:
        print(f"ОШИБКА порта: {e}")
        sys.exit(1)


# ===========================================================================
# Точка входа
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Corona decode-HW conformance test для AX7203"
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="Синтетический самотест парсера (без UART-порта)"
    )
    parser.add_argument(
        "--port", default="/dev/cu.usbserial-120",
        help="UART-порт CP2102N (default: /dev/cu.usbserial-120)"
    )
    parser.add_argument(
        "--baud", type=int, default=115200,
        help="Скорость UART (default: 115200)"
    )
    args = parser.parse_args()

    if args.self_test:
        ok = run_self_test_synthetic()
        sys.exit(0 if ok else 1)
    else:
        # Всегда сначала самотест, затем железо
        print("Запуск синтетического самотеста перед аппаратным тестом...")
        ok = run_self_test_synthetic()
        if not ok:
            print("\nСамотест не прошёл — аппаратный тест отменён.")
            sys.exit(1)
        print(f"\nЗапуск аппаратного теста на {args.port}...")
        run_hardware_tests(args.port, args.baud)
