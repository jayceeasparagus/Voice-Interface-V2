#!/bin/sh
set -eu

IFACE="${DOG_WIRED_IFACE:-eth0}"
ADDR="${DOG_WIRED_IP:-10.42.0.1}"
CIDR="${DOG_WIRED_CIDR:-24}"
NETMASK="${DOG_WIRED_NETMASK:-255.255.255.0}"

echo "Configuring dog wired link: $IFACE -> $ADDR/$CIDR"

if command -v ip >/dev/null 2>&1; then
  ip link set "$IFACE" up
  ip addr replace "$ADDR/$CIDR" dev "$IFACE"
  ip addr show "$IFACE"
else
  ifconfig "$IFACE" "$ADDR" netmask "$NETMASK" up
  ifconfig "$IFACE"
fi
