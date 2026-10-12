#!/bin/sh
# /data/autostart/90-brushpatch.sh
# Side-brush alert patch, safe persistent deploy.
#
# NOT named deebot.sh on purpose: the stock /etc/rc.d/deebot.sh launcher runs
# untouched (keeps its restart loop). This script only overlays the patched
# liberos_node_alert.so and nudges deebot to reload it. All work is backgrounded
# so autostart.sh / boot can never wedge on it.
#
# Disable: remove this file and reboot (or: umount the bind + killall deebot).

SRC=/data/patch/liberos_node_alert.so
DST=/usr/lib/node/liberos_node_alert.so

load () {
	(
		# let the normal boot / deebot startup settle first
		sleep 20
		[ -f "$SRC" ] || exit 0
		if ! mount | grep -q "$DST"; then
			mount --bind "$SRC" "$DST"
			# deebot already loaded the stock node; reload it so the patched
			# one is dlopen'd. The stock deebot.sh loop relaunches deebot.
			[ -n "$(pidof deebot)" ] && killall deebot
		fi
	) &
}

unload () {
	mount | grep -q "$DST" && umount "$DST" 2>/dev/null
}

case "$1" in
	start)   load ;;
	stop)    unload ;;
	restart) unload; load ;;
	*)       echo "$0 <start/stop/restart>" ;;
esac
