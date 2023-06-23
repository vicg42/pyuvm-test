#!/bin/sh

sudo apt-get update
sudo apt-get install iverilog

alias icarus=iverilog


#CentOS
#sudo yum makecache
#sudo yum -y install autoconf
#sudo yum -y install git help2man perl python3 make autoconf g++ flex bison ccache
#sudo yum -y install libgoogle-perftools-dev numactl perl-doc
#sudo yum -y install libfl2
#sudo yum -y install libfl-dev
#sudo yum -y install zlibc zlib1g zlib1g-dev

#git clone https://github.com/verilator/verilator
# Every time you need to build:
#unsetenv VERILATOR_ROOT  # For csh; ignore error if on bash
#unset VERILATOR_ROOT  # For bash
#cd verilator
#git pull         # Make sure git repository is up-to-date
#git checkout v4.106      # Use most recent stable release

#autoconf         # Create ./configure script
#./configure      # Configure and create Makefile
#make -j `nproc`  # Build Verilator itself (if error, try just 'make')
#sudo make install