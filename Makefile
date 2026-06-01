# SPDX-License-Identifier: Apache-2.0
# tt-trinity-corona / Makefile

.PHONY: all test lint verilator-lint formal gls rom-golden clean

all: lint verilator-lint

test:
	$(MAKE) -C test

lint:
	@echo "--- Verilog lint (iverilog -t null) ---"
	iverilog -t null -Wall -g2012 src/rtl/*.v

verilator-lint:
	@echo "--- Verilator lint (zero warnings) ---"
	verilator --lint-only -Wall -Isrc/rtl src/rtl/*.v

formal:
	$(MAKE) -C formal all SBY=sby

gls:
	@echo "--- GLS: synthesize + simulate ---"
	yosys -p "read_verilog src/rtl/*.v; synth -top tt_um_trinity_corona -flatten; write_verilog -noattr /tmp/corona_synth.v" 2>&1 | tail -3
	iverilog -o /tmp/corona_gls "$$(yosys-config --datdir)/simcells.v" /tmp/corona_synth.v test/tb_gls_smoke.v
	vvp /tmp/corona_gls 2>&1 | tee /tmp/gls.log
	grep -q "ALL PASS" /tmp/gls.log

rom-golden:
	@echo "--- ROM golden: exhaustive 80-record validation ---"
	yosys -p "read_verilog src/rtl/*.v; synth -top tt_um_trinity_corona -flatten; write_verilog -noattr /tmp/corona_synth.v" 2>&1 | tail -3
	iverilog -o /tmp/rom_golden "$$(yosys-config --datdir)/simcells.v" /tmp/corona_synth.v test/tb_rom_golden.v
	vvp /tmp/rom_golden 2>&1 | tee /tmp/rom_golden.log
	grep -q "ALL 80 RECORDS PASS" /tmp/rom_golden.log

clean:
	$(MAKE) -C test clean
	rm -rf sim_build results.xml
