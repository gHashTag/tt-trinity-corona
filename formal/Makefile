# SPDX-License-Identifier: Apache-2.0
# formal/Makefile -- Run SymbiYosys formal proofs for all Corona decoders.
# Requires: sby (SymbiYosys), yosys, z3

SBY ?= sby
RTL := ../src/rtl

TARGETS := fv_int4 fv_int8 fv_e8m0 fv_bf16 fv_fp8_e5m2 \
           fv_fp8_e4m3_fnuz fv_mxfp8_e4m3 fv_mxint8 \
           fv_posit8 fv_bcd fv_fp6_e3m2 \
           fv_tf32 fv_lns8 fv_fp6_e2m3 fv_fp4 fv_nf4 fv_bitnet \
           fv_fsm fv_rom

.PHONY: all clean $(TARGETS)

all: $(TARGETS)
	@echo "=== ALL FORMAL PROOFS PASSED ==="

$(TARGETS): %:
	@echo "--- Proving $@ ---"
	$(SBY) -f $@.sby

clean:
	rm -rf $(addsuffix _bmc, $(TARGETS))
