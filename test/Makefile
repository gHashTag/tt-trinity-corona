# SPDX-License-Identifier: Apache-2.0
# cocotb simulation Makefile for tt-trinity-corona

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files -- update when adding new RTL modules
PROJECT_SOURCES = tt_um_trinity_corona.v format_rom.v \
	bf16_decode.v mxfp8_e4m3_decode.v bcd_decode.v lns8_decode.v posit8_decode.v \
	fp4_decode.v fp6_e3m2_decode.v nf4_decode.v tf32_decode.v fp8_e5m2_decode.v \
	fp6_e2m3_decode.v int8_decode.v e8m0_decode.v mxint8_decode.v fp8_e4m3_fnuz_decode.v \
	bitnet_decode.v
SRC_DIR = $(PWD)/../src/rtl
VERILOG_SOURCES = $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

TOPLEVEL = tt_um_trinity_corona
MODULE = test_anchor,test_decoders,test_stress

include $(shell cocotb-config --makefiles)/Makefile.sim
