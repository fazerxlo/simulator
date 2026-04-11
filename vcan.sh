#!/usr/bin/env bash

set -eou pipefail

function help {
   echo "Configure vcan"
   echo
   echo "Syntax: vcan.sh [-k|h|]"
   echo "options:"
   echo "h     Print this Help."
   echo "v     Verbose mode."
   echo "k     Close and kill vcan interface"
   echo ""
}

function vcan_kill {
    sudo ip link show dev vcan0 &>/dev/null && sudo ip link set dev vcan0 down || true
    sudo modprobe -r vcan || true
}

function vcan_start {
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set dev vcan0 up
}


while getopts ":hvk" option; do
   case $option in
      h) # display Help
         help
         exit;;
      v) # display Help
         set -x;;
      k) # display Help
         vcan_kill
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

vcan_kill
vcan_start
