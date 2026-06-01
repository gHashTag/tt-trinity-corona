# tools/synth_stat.tcl -- Yosys synthesis script for area estimation.
# Usage: yosys -c tools/synth_stat.tcl
# With GF180MCU Liberty: LIB=$PDK_ROOT/.../gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib yosys -c tools/synth_stat.tcl

read_verilog src/rtl/tt_um_trinity_corona.v
read_verilog src/rtl/format_rom.v
read_verilog src/rtl/bf16_decode.v
read_verilog src/rtl/mxfp8_e4m3_decode.v
read_verilog src/rtl/bcd_decode.v
read_verilog src/rtl/lns8_decode.v
read_verilog src/rtl/posit8_decode.v
read_verilog src/rtl/fp4_decode.v
read_verilog src/rtl/fp6_e3m2_decode.v
read_verilog src/rtl/nf4_decode.v
read_verilog src/rtl/tf32_decode.v
read_verilog src/rtl/fp8_e5m2_decode.v
read_verilog src/rtl/fp6_e2m3_decode.v
read_verilog src/rtl/int8_decode.v
read_verilog src/rtl/e8m0_decode.v
read_verilog src/rtl/mxint8_decode.v

hierarchy -check -top tt_um_trinity_corona
proc; opt; fsm; opt; memory; opt
techmap; opt

if { [info exists ::env(LIB)] } {
    dfflibmap -liberty $::env(LIB)
    abc -liberty $::env(LIB) -D 20000
    stat -liberty $::env(LIB)
} else {
    abc
    stat
}

clean
