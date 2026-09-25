#!/usr/bin/env bash

set -eou pipefail

DEVICE=""

function help {
   echo "Configure slcan"
   echo
   echo "Syntax: slcan.sh [-d <device>|-k|-h|-v]"
   echo "options:"
   echo "d <dev> Specify ttyUSB device (e.g. /dev/ttyUSB0 or ttyUSB0)."
   echo "h       Print this Help."
   echo "v       Verbose mode."
   echo "k       Close and kill slcan interface and daemon"
   echo ""
}

function slcan_kill {
    sudo ip link set dev can0 down || true
    sudo killall slcand  || true
}

function slcan_start {
    if [[ -n "${DEVICE}" ]]; then
        if [[ "${DEVICE}" == /* ]]; then
            usb_ttl_path="${DEVICE}"
        else
            usb_ttl_path="/dev/${DEVICE}"
        fi
    else
        usb_ttl_path=$(ls /dev/ttyUSB* 2>/dev/null | head -n 1 || true)
    fi

    if [[ -z "${usb_ttl_path}" || ! -e "${usb_ttl_path}" ]]; then
        echo "Error: Device '${DEVICE:-/dev/ttyUSB*}' not found" >&2
        exit 1
    fi

    usb_ttl=$(basename "${usb_ttl_path}")

    sudo slcan_attach -f -s6 -o "${usb_ttl_path}"
    sudo slcand -S 1000000 "${usb_ttl}" can0  
    sudo ip link set dev can0 up
}


while getopts ":d:hvk" option; do
   case $option in
      d)
         DEVICE="$OPTARG";;
      h) # display Help
         help
         exit;;
      v) # display Help
         set -x;;
      k) # display Help
         slcan_kill
         exit;;
      :) # Missing argument
         echo "Error: Option -$OPTARG requires an argument"
         exit 1;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit 1;;
   esac
done

slcan_kill
slcan_start

