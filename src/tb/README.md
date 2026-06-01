# src/tb/

Gate-level simulation testbench. The primary test suite is in `test/` (cocotb).

## Actual CI gates

| Gate | What it checks |
| --- | --- |
| Verilator lint | Zero warnings on all RTL |
| Yosys synthesis | Cell count, timing at 25 MHz |
| SymbiYosys formal | 19 configs, 57 tasks (bmc + prove + cover) |
| cocotb tests | 48 tests (anchor + decoders + stress) |
| GLS smoke | 76 golden vectors against Yosys-synthesized netlist |
| ROM golden | 80-record sweep vs golden reference |
| GDS hardening | LibreLane 3.x on GF180MCU |
| GL tests | 48 cocotb tests against GDS netlist |
| Precheck | TT pin/power/DRC/antenna validation |
