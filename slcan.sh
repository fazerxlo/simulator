#!/usr/bin/env bash

set -eou pipefail

function help {
   echo "Configure slcan"
   echo
   echo "Syntax: slcan.sh [-k|h|]"
   echo "options:"
   echo "h     Print this Help."
   echo "v     Verbose mode."
   echo "k     Close and kill slcan interface and demon"
   echo ""
}

function slcan_kill {
    sudo ip link set dev can0 down || true
    sudo killall slcand  || true
}

function slcan_start {
    usb_ttl_path=$(ls /dev/ttyUSB*)
    usb_ttl=$(basename "${usb_ttl_path}")

    sudo slcan_attach -f -s6 -o "${usb_ttl_path}"
    sudo slcand -S 1000000 "${usb_ttl}" can0  
    sudo ip link set dev can0 up
}


while getopts ":hvk" option; do
   case $option in
      h) # display Help
         help
         exit;;
      v) # display Help
         set -x;;
      k) # display Help
         slcan_kill
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

slcan_kill
slcan_start

