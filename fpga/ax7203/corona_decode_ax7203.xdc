# corona_decode_ax7203.xdc
# Автор: Vasilev
# Назначение: pin constraints и timing для AX7203 (xc7a200tfbg484-2)
# АППАРАТНЫЕ КОНСТАНТЫ — не редактировать без осциллографа/схемы платы.
#
# Проверено: IDCODE на плате = 0x13636093 (Artix-7 200T fbg484)
#            НЕ путать с QMTECH IDCODE 0x0362D093
#
# ===========================================================================
# Клок: 200 МГц LVDS дифф. пара R4(+) / T4(-)
# Стандарт DIFF_SSTL15 (VCCaux = 1.5 В, банк HR-0 на AX7203)
# ===========================================================================
set_property -dict { PACKAGE_PIN R4  IOSTANDARD DIFF_SSTL15 } [get_ports sys_clk_p]
set_property -dict { PACKAGE_PIN T4  IOSTANDARD DIFF_SSTL15 } [get_ports sys_clk_n]

create_clock -name sys_clk -period 5.000 -waveform {0.000 2.500} [get_ports sys_clk_p]

# ===========================================================================
# Сброс: T6, active-low, LVCMOS15
# (На AX7203 кнопка сброса — банк HR-0, Vcco = 1.5 В)
# ===========================================================================
set_property -dict { PACKAGE_PIN T6  IOSTANDARD LVCMOS15 } [get_ports sys_rst_n]

# ===========================================================================
# UART: LVCMOS33 (USB-UART CP2102N через банк HP-14 или HR-34, Vcco = 3.3 В)
#   TX выход FPGA = N15, RX вход FPGA = P20
# ===========================================================================
set_property -dict { PACKAGE_PIN N15 IOSTANDARD LVCMOS33 SLEW SLOW DRIVE 4 } [get_ports uart_tx]
set_property -dict { PACKAGE_PIN P20 IOSTANDARD LVCMOS33 } [get_ports uart_rx]

# ===========================================================================
# LED: LVCMOS18 (банк HR-35, Vcco = 1.8 В)
#   B13=led[0], C13=led[1], D14=led[2], D15=led[3]
#   КРИТИЧНО: НЕ LVCMOS33 — перепутанный стандарт повреждает банк.
# ===========================================================================
set_property -dict { PACKAGE_PIN B13 IOSTANDARD LVCMOS18 SLEW SLOW DRIVE 4 } [get_ports {led[0]}]
set_property -dict { PACKAGE_PIN C13 IOSTANDARD LVCMOS18 SLEW SLOW DRIVE 4 } [get_ports {led[1]}]
set_property -dict { PACKAGE_PIN D14 IOSTANDARD LVCMOS18 SLEW SLOW DRIVE 4 } [get_ports {led[2]}]
set_property -dict { PACKAGE_PIN D15 IOSTANDARD LVCMOS18 SLEW SLOW DRIVE 4 } [get_ports {led[3]}]

# ===========================================================================
# Timing: false path на синхронизатор сброса
#   sys_rst_n — асинхронный внешний сигнал, первый FF — rst_meta.
#   Vivado не должен анализировать setup/hold через этот путь.
# ===========================================================================
set_false_path -from [get_ports sys_rst_n] -to [get_cells {u_top/rst_meta_reg}]

# Альтернативная форма (если иерархия меняется):
# set_false_path -from [get_ports sys_rst_n]

# ===========================================================================
# Timing: UART RX вход — false path (асинхронный внешний сигнал)
#   rx_meta — первый синхронизирующий FF в corona_decode_top_ax7203.
# ===========================================================================
set_false_path -from [get_ports uart_rx] -to [get_cells {u_top/rx_meta_reg}]

# ===========================================================================
# BITSTREAM: параметры для прошивки через openocd
#   compress=TRUE — уменьшает размер .bit для ускорения загрузки
# ===========================================================================
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.UNUSEDPIN PULLDOWN [current_design]

# ===========================================================================
# Примечание по setup/hold:
#   При использовании IBUFDS без MMCM/PLL джиттер клока не скомпенсирован.
#   Vivado завершит синтез, но timing closure при 200 МГц не гарантирован
#   без анализа WNS/WHS из timing report. Если WNS < 0, добавить MMCM.
# ===========================================================================
