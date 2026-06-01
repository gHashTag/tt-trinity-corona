# SPDX-License-Identifier: Apache-2.0
# tt-trinity-corona / Makefile

.PHONY: test lint clean

test:
	$(MAKE) -C test

lint:
	@echo "--- Verilog lint (iverilog -t null) ---"
	iverilog -t null -Wall -g2012 src/rtl/*.v

clean:
	$(MAKE) -C test clean
	rm -rf sim_build results.xml
