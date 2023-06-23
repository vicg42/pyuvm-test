CWD=$(shell pwd)
export COCOTB_REDUCED_LOG_FMT = 1
SIM ?= icarus
#SIM ?= verilator
TOPLEVEL_LANG ?= verilog
ifeq ($(TOPLEVEL_LANG),verilog)
	VERILOG_SOURCES +=$(CWD)/hdl/verilog/tinyalu.sv
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif
MODULE := testbench
TOPLEVEL = tinyalu
GHDL_ARGS := --ieee=synopsys
COCOTB_HDL_TIMEUNIT = 1us
COCOTB_HDL_TIMEPRECISION = 1us
include $(shell cocotb-config --makefiles)/Makefile.sim
include $(CWD)/cleanall.mk
