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
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # CMD mode (bits [7:6]=00) with fmt_id = 0x7F (bits [6:0])
    dut.ui_in.value = 0x7F
    await RisingEdge(dut.clk)
    # Combinational output: read immediately
    await cocotb.triggers.Timer(1, unit="ns")

    uo = dut.uo_out.value.to_unsigned()
    uio = dut.uio_out.value.to_unsigned()
    combined = (uio << 8) | uo

    assert uo == 0xC0, f"uo_out expected 0xC0, got 0x{uo:02X}"
    assert uio == 0x47, f"uio_out expected 0x47, got 0x{uio:02X}"
    assert combined == 0x47C0, f"anchor expected 0x47C0, got 0x{combined:04X}"
    dut._log.info(f"PASS: anchor = 0x{combined:04X}")


@cocotb.test()
async def test_anchor_stable_across_cycles(dut):
    """Anchor output remains stable while CMD+0x7F is held."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = 0x7F
    for cycle in range(10):
        await RisingEdge(dut.clk)
        await cocotb.triggers.Timer(1, unit="ns")
        uo = dut.uo_out.value.to_unsigned()
        uio = dut.uio_out.value.to_unsigned()
        combined = (uio << 8) | uo
        assert combined == 0x47C0, f"cycle {cycle}: expected 0x47C0, got 0x{combined:04X}"
    dut._log.info("PASS: anchor stable across 10 cycles")


@cocotb.test()
async def test_non_anchor_returns_zero(dut):
    """CMD with fmt_id != 0x7F should not produce the anchor value."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for fmt_id in [0x00, 0x01, 0x4C, 0x7E]:
        dut.ui_in.value = fmt_id  # mode=00, fmt_id varies
        await RisingEdge(dut.clk)
        await cocotb.triggers.Timer(1, unit="ns")
        uo = dut.uo_out.value.to_unsigned()
        uio = dut.uio_out.value.to_unsigned()
        combined = (uio << 8) | uo
        assert combined != 0x47C0, f"fmt_id=0x{fmt_id:02X} should not produce anchor"
    dut._log.info("PASS: non-anchor fmt_ids do not produce 0x47C0")


@cocotb.test()
async def test_reset_clears_state(dut):
    """After reset, outputs should be zero (no anchor asserted)."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)

    uo = dut.uo_out.value.to_unsigned()
    assert uo == 0, f"after reset, uo_out expected 0, got 0x{uo:02X}"
    dut._log.info("PASS: reset clears outputs")
