#!/bin/sh
set -eu

IFACE="${BOARD_WIRED_IFACE:-eth0}"
ADDR="${BOARD_WIRED_IP:-10.42.0.2}"
NETMASK="${BOARD_WIRED_NETMASK:-255.255.255.0}"

echo "Configuring board wired link: $IFACE -> $ADDR/$NETMASK"
ifconfig "$IFACE" "$ADDR" netmask "$NETMASK" up
ifconfig "$IFACE"
