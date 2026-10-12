#!/bin/sh
# /data/autostart/00-decloud.sh
# De-cloud an Ecovacs PX30 (T8 AIVI / "deboot", model=dxai, platform=px30).
#
# This firmware has NO iptables (only /sbin/ip), so we blackhole the whole
# internet with two /1 routes. They are more specific than the /0 default
# route, so they win; the LAN on-link route (e.g. 192.168.0.0/24) is more
# specific still, so the LAN keeps working. dhcpcd only manages the default
# route, so it cannot undo these.
#
# Runs at boot via the /data/autostart/*.sh hook (confirmed active on this unit).
# Reversible: delete this file and reboot.

ip route add blackhole 0.0.0.0/1   2>/dev/null   # covers 0.0.0.0 - 127.255.255.255
ip route add blackhole 128.0.0.0/1 2>/dev/null   # covers 128.0.0.0 - 255.255.255.255
ip -6 route add blackhole ::/0     2>/dev/null   # IPv6 (harmless if IPv6 unused)
