# SPDX-License-Identifier: Apache-2.0
# tt-trinity-corona / src/constraint.sdc
# Timing constraints for LibreLane GDS hardening (GF180MCU, 25 MHz).

# Primary clock: 40 ns period (25 MHz)
create_clock -name clk -period 40.0 [get_ports clk]

# Input delays: assume host drives inputs within 25% of clock period
set_input_delay -clock clk -max 10.0 [get_ports {ui_in[*] uio_in[*] rst_n ena}]
set_input_delay -clock clk -min  1.0 [get_ports {ui_in[*] uio_in[*] rst_n ena}]

# Output delays: allow 25% of clock period for downstream capture
set_output_delay -clock clk -max 10.0 [get_ports {uo_out[*] uio_out[*] uio_oe[*]}]
set_output_delay -clock clk -min  0.0 [get_ports {uo_out[*] uio_out[*] uio_oe[*]}]

# Max transition: limit slew to avoid slew violations
set_max_transition 10.0 [current_design]

# Max fanout: limit fanout to reduce buffering stress
set_max_fanout 16 [current_design]
