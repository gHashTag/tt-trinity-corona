# SPDX-License-Identifier: Apache-2.0
# test/test_anchor.py -- cocotb test for TG-TRIAD-X anchor probe (0x47C0).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0x80  # bit7=1 keeps FSM in IDLE after reset
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_anchor_probe(dut):
    """Anchor probe: CMD with fmt_id=0x7F -> {uio_out, uo_out} == 0x47C0."""
    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # CMD mode (bits [7:6]=00) with fmt_id = 0x7F (bits [6:0])
    dut.ui_in.value = 0x7F
    await RisingEdge(dut.clk)
    # Combinational output: read immediately
    await cocotb.triggers.Timer(1, units="ns")

    uo = dut.uo_out.value.integer
    uio = dut.uio_out.value.integer
    combined = (uio << 8) | uo

    oe = dut.uio_oe.value.integer

    assert uo == 0xC0, f"uo_out expected 0xC0, got 0x{uo:02X}"
    assert uio == 0x47, f"uio_out expected 0x47, got 0x{uio:02X}"
    assert combined == 0x47C0, f"anchor expected 0x47C0, got 0x{combined:04X}"
    assert oe == 0xFF, f"uio_oe expected 0xFF during anchor, got 0x{oe:02X}"
    dut._log.info(f"PASS: anchor = 0x{combined:04X}, uio_oe = 0x{oe:02X}")


@cocotb.test()
async def test_anchor_stable_across_cycles(dut):
    """Anchor output remains stable while CMD+0x7F is held."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 0x7F
    for cycle in range(10):
        await RisingEdge(dut.clk)
        await cocotb.triggers.Timer(1, units="ns")
        uo = dut.uo_out.value.integer
        uio = dut.uio_out.value.integer
        combined = (uio << 8) | uo
        assert combined == 0x47C0, f"cycle {cycle}: expected 0x47C0, got 0x{combined:04X}"
    dut._log.info("PASS: anchor stable across 10 cycles")


@cocotb.test()
async def test_non_anchor_returns_zero(dut):
    """CMD with fmt_id != 0x7F should not produce the anchor value."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for fmt_id in [0x00, 0x01, 0x4C, 0x7E]:
        dut.ui_in.value = fmt_id  # mode=00, fmt_id varies
        await RisingEdge(dut.clk)
        await cocotb.triggers.Timer(1, units="ns")
        uo = dut.uo_out.value.integer
        uio = dut.uio_out.value.integer
        oe = dut.uio_oe.value.integer
        combined = (uio << 8) | uo
        assert combined != 0x47C0, f"fmt_id=0x{fmt_id:02X} should not produce anchor"
        assert oe == 0x00, f"fmt_id=0x{fmt_id:02X}: uio_oe should be 0x00, got 0x{oe:02X}"
    dut._log.info("PASS: non-anchor fmt_ids produce zero output + OE")


@cocotb.test()
async def test_reset_clears_state(dut):
    """After reset, outputs should be zero (no anchor asserted)."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)

    uo = dut.uo_out.value.integer
    assert uo == 0, f"after reset, uo_out expected 0, got 0x{uo:02X}"
    dut._log.info("PASS: reset clears outputs")


@cocotb.test()
async def test_ena_gate_freezes_fsm(dut):
    """When ena=0, FSM must not advance — TT mux requires this."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # Start a decode transaction (CMD1)
    dut.ui_in.value = 0x2F  # fmt_id=47 (INT8)
    await RisingEdge(dut.clk)
    # Now in CMD2 state. Deassert ena.
    dut.ena.value = 0
    dut.ui_in.value = 0x01  # byte_count=1
    # Clock 10 cycles with ena=0 — FSM should not advance
    await ClockCycles(dut.clk, 10)
    # Re-enable and continue normally
    dut.ena.value = 1
    await RisingEdge(dut.clk)
    # Send data byte
    dut.ui_in.value = 0x2A  # 42
    await RisingEdge(dut.clk)
    # Read result
    await cocotb.triggers.Timer(1, units="ns")
    result = []
    for _ in range(4):
        await cocotb.triggers.Timer(1, units="ns")
        result.append(dut.uo_out.value.integer)
        await RisingEdge(dut.clk)
    got = result[0] | (result[1] << 8) | (result[2] << 16) | (result[3] << 24)
    import struct
    expected = struct.unpack('>I', struct.pack('>i', 42))[0]
    assert got == expected, \
        f"ena gate: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: ena=0 freezes FSM, decode correct after re-enable")
